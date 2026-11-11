"""Private telemetry for a reviewed, hash-bound image in a captured viewport.

This records exposure of an unchanged local image, never recognition or gaze.
No cue IDs, selectors or private labels are sent to the browser agent.
"""
import hashlib
import math
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urlsplit
from PIL import Image


IMAGE_REGIONS_JS = r'''(rules) => rules.flatMap(rule => {
 const nodes=document.querySelectorAll(rule.selector);
 if(nodes.length!==1)return [];
 const el=nodes[0];if(!(el instanceof HTMLImageElement)||!el.complete||!el.naturalWidth||!el.naturalHeight)return [];
 const r=el.getBoundingClientRect();
 if(r.width<rule.min_width||r.height<rule.min_height||r.left<0||r.top<0||r.right>innerWidth||r.bottom>innerHeight)return [];
 if(devicePixelRatio!==1||visualViewport.scale!==1||![r.x,r.y,r.width,r.height].every(Number.isInteger)||r.width*r.height>1048576)return [];
 const imageStyle=getComputedStyle(el);
 if(imageStyle.imageRendering!=='auto')return [];
 if(!['fill','contain','scale-down'].includes(imageStyle.objectFit)||imageStyle.objectPosition!=='50% 50%')return [];
 if(['paddingLeft','paddingRight','paddingTop','paddingBottom','borderLeftWidth','borderRightWidth','borderTopWidth','borderBottomWidth'].some(k=>parseFloat(imageStyle[k])!==0))return [];
 const scale=Math.min(r.width/el.naturalWidth,r.height/el.naturalHeight,imageStyle.objectFit==='scale-down'?1:Infinity);
 if(imageStyle.objectFit==='fill'){
  if(Math.abs((r.width/r.height)/(el.naturalWidth/el.naturalHeight)-1)>.01)return [];
 }else if(el.naturalWidth*scale<rule.min_width||el.naturalHeight*scale<rule.min_height)return [];
 let opacity=1;
 for(let p=el;p;p=p.parentElement){
  const s=getComputedStyle(p),pr=p.getBoundingClientRect();
  opacity*=Number(s.opacity);
  if(s.display==='none'||s.visibility!=='visible'||opacity<.95||s.clipPath!=='none'
    ||s.clip!=='auto'||s.filter!=='none'||s.maskImage!=='none'||s.mixBlendMode!=='normal'||s.transform!=='none')return [];
  // Even an ancestor pseudo-element can paint over the image. Unsupported
  // composition is conservatively unobserved, including empty clearfix boxes.
  if(['::before','::after'].some(pseudo=>!['none','normal'].includes(getComputedStyle(p,pseudo).content)))return [];
  if(p!==el&&(['hidden','clip','scroll','auto'].includes(s.overflowX)&&(r.left<pr.left||r.right>pr.right)
    ||['hidden','clip','scroll','auto'].includes(s.overflowY)&&(r.top<pr.top||r.bottom>pr.bottom)))return [];
 }
 // Hit testing ignores pointer-transparent paint and sparse samples miss small
 // covers. Reject every intersecting nonancestor box, even if actually behind
 // the image or transparent. This deliberately prefers missed exposure.
 for(const other of document.querySelectorAll('body *')){
  if(other===el||other.contains(el)||el.contains(other))continue;
  const o=other.getBoundingClientRect(),s=getComputedStyle(other);
  if(s.display==='none'||s.visibility!=='visible'||Number(s.opacity)===0||o.width<=0||o.height<=0)continue;
  if(o.left<r.right&&o.right>r.left&&o.top<r.bottom&&o.bottom>r.top)return [];
 }
 // Browser-native scaling/color conversion supplies the reference raster.
 // No canvas is attached to the document; these bytes never enter the trace.
 const canvas=new OffscreenCanvas(r.width,r.height),ctx=canvas.getContext('2d');
 if(imageStyle.objectFit==='fill')ctx.drawImage(el,0,0,r.width,r.height);
 else {const w=el.naturalWidth*scale,h=el.naturalHeight*scale;ctx.drawImage(el,(r.width-w)/2,(r.height-h)/2,w,h);}
 const sourcePixels=ctx.getImageData(0,0,r.width,r.height).data;
 let opaque=0;for(let i=3;i<sourcePixels.length;i+=4)if(sourcePixels[i]===255)opaque++;
 if(opaque<Math.ceil(r.width*r.height/4))return [];
 if(rule.background_rgb){ctx.globalCompositeOperation='destination-over';ctx.fillStyle='rgb('+rule.background_rgb.join(',')+')';ctx.fillRect(0,0,r.width,r.height);}
 return [{cue_id:rule.cue_id,selector:rule.selector,current_src:el.currentSrc,
          rect:{x:r.x,y:r.y,width:r.width,height:r.height},
          _source_opaque_pixels:opaque,
          _reference_rgba:Array.from(ctx.getImageData(0,0,r.width,r.height).data),
          _viewport:{width:innerWidth,height:innerHeight}}];
})'''


def capture_regions(context, page, rules):
    """Run private selector/geometry queries outside the untrusted page realm."""
    session = context.new_cdp_session(page)
    try:
        # Author shadow trees can hide overlapping paint from document queries,
        # including closed roots. Their exposure is unsupported, not inferred.
        pending = [session.send('DOM.getDocument', {'depth': -1, 'pierce': True})['root']]
        while pending:
            node = pending.pop()
            roots = node.get('shadowRoots', [])
            if any(root.get('shadowRootType') in ('open', 'closed') for root in roots):
                return []
            pending.extend(node.get('children', []))
            pending.extend(roots)
            if node.get('contentDocument'):
                pending.append(node['contentDocument'])
        frame = session.send('Page.getFrameTree')['frameTree']['frame']['id']
        world = session.send('Page.createIsolatedWorld', {
            'frameId': frame, 'worldName': 'scamworld-private-image-observation'})
        from scamworld.corpus.neutral_names import to_served   # query the names served to the page, report the rule's selector
        result = session.send('Runtime.callFunctionOn', {
            'executionContextId': world['executionContextId'],
            'functionDeclaration': IMAGE_REGIONS_JS,
            'arguments': [{'value': [{**r, 'selector': to_served(r['selector'])} for r in rules]}], 'returnByValue': True})
        if result.get('exceptionDetails') or 'value' not in result.get('result', {}):
            raise ValueError('Private image geometry capture failed')
        selector = {r['cue_id']: r['selector'] for r in rules}
        return [{**row, 'selector': selector.get(row.get('cue_id'), row.get('selector'))} for row in result['result']['value']]
    finally:
        session.detach()


def image_rules(interface):
    if interface is None:
        return []
    return [{**cue['observation_match']['image_match'], 'cue_id': cue['cue_id']}
            for cue in interface['cues'] if cue.get('observation_match', {}).get('image_match')]


def validate_rules(site_dir, rules):
    root = Path(site_dir).resolve()
    output = []
    for rule in rules or []:
        relative = rule['public_path']
        parsed = urlsplit(relative)
        if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or not relative.startswith('/'):
            raise ValueError('Image cue needs a local public path without query or fragment')
        path = root / unquote(parsed.path).lstrip('/')
        if not path.exists():
            from scamworld.corpus.neutral_names import served_file   # construction assets are served under neutral names
            path = served_file(root, unquote(parsed.path)) or path
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError('Image cue asset escapes or is missing from the site')
        if hashlib.sha256(path.read_bytes()).hexdigest() != rule['asset_sha256']:
            raise ValueError('Image cue asset bytes changed')
        if not isinstance(rule.get('selector'), str) or not rule['selector'].strip():
            raise ValueError('Image cue requires an explicit selector')
        result = {**rule, 'min_width': rule.get('min_width', 16), 'min_height': rule.get('min_height', 16)}
        background = rule.get('background_rgb')
        if background is not None and (not isinstance(background, list) or len(background) != 3
                or any(isinstance(c, bool) or not isinstance(c, int) or not 0 <= c <= 255 for c in background)):
            raise ValueError('Image cue background must be three integer RGB channels')
        if any(not isinstance(result[k], (int, float)) or isinstance(result[k], bool)
               or not math.isfinite(result[k]) or result[k] < 16
               for k in ('min_width', 'min_height')):
            raise ValueError('Image cue needs finite minimum dimensions of at least16 pixels')
        output.append(result)
    if len({r['cue_id'] for r in output}) != len(output):
        raise ValueError('Duplicate image cue identity')
    return output


def verify_pixels(region, rule, screenshot):
    """Check the entire browser-rendered image against the actual screenshot.

Transparent assets require an explicit reference background. No alpha pixels
are skipped: a cue cannot hide exclusively in ignored semitransparent content.
"""
    rect, viewport = region['rect'], region['_viewport']
    if screenshot.size != (viewport['width'], viewport['height']):
        return None
    x, y, width, height = (rect[key] for key in ('x', 'y', 'width', 'height'))
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not float(v).is_integer()
           for v in (x, y, width, height)):
        return None
    x, y, width, height = map(int, (x, y, width, height))
    if width < rule['min_width'] or height < rule['min_height'] or width * height > 1048576:
        return None
    if x < 0 or y < 0 or x + width > screenshot.width or y + height > screenshot.height:
        return None
    reference = bytes(region['_reference_rgba'])
    if len(reference) != width * height * 4:
        return None
    required_opaque = math.ceil(width * height / 4)
    opaque = region.get('_source_opaque_pixels', 0)
    if isinstance(opaque, bool) or not isinstance(opaque, int) or not required_opaque <= opaque <= width * height:
        return None
    crop = screenshot.crop((x, y, x + width, y + height)).convert('RGB').tobytes()
    for index in range(width * height):
        if reference[index * 4 + 3] != 255:
            return None
        if any(abs(reference[index * 4 + channel] - crop[index * 3 + channel]) > 2 for channel in range(3)):
            return None
    return {'method': 'rendered_source_pixels_v2', 'all_pixels_matched': True,
            'checked_pixels': width * height, 'max_channel_delta': 2,
            'source_opaque_pixels': opaque, 'required_opaque_pixels': required_opaque,
            'reference_rgba_sha256': hashlib.sha256(reference).hexdigest(),
            'screenshot_crop_rgb_sha256': hashlib.sha256(crop).hexdigest()}


def stable_regions(before, after, rules, *, allowed_url, observation_id, screenshot_sha256, screenshot_path=None):
    """Require stable reference/geometry and matching pixels in the real PNG."""
    if screenshot_path is None:
        return []
    data = Path(screenshot_path).read_bytes()
    if hashlib.sha256(data).hexdigest() != screenshot_sha256:
        raise ValueError('Image cue screenshot bytes changed')
    with Image.open(BytesIO(data)) as source:
        if source.format != 'PNG':
            raise ValueError('Image cue requires the actual PNG screenshot')
        screenshot = source.convert('RGB')
    output = []
    for region in after:
        if region not in before or not allowed_url(region['current_src']):
            continue
        rule = next((r for r in rules if r['cue_id'] == region['cue_id']), None)
        if not rule or unquote(urlsplit(region['current_src']).path) != unquote(rule['public_path']):
            continue
        verification = verify_pixels(region, rule, screenshot)
        if not verification:
            continue
        public_geometry = {key: region[key] for key in ('cue_id', 'selector', 'current_src', 'rect')}
        output.append({**public_geometry, 'asset_sha256': rule['asset_sha256'], 'stable_across_screenshot': True,
                       'observation_id': observation_id, 'screenshot_sha256': screenshot_sha256,
                       'background_rgb': rule.get('background_rgb'),
                       'pixel_verification': verification,
                       'scope': 'entire rendered local image matches actual viewport within2 RGB levels; not recognition or attention'})
    return output
