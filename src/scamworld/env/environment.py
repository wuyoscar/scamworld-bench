"""Versioned source-derived tasks using actual BrowserGym and visited-text evidence."""
from pathlib import Path
import json
from urllib.parse import urlparse,urljoin
from scamworld.corpus.neutral_names import to_served
from scamworld.env.runtime import GUARD_JS
from scamworld.env.runtime import BrowserRuntime, ROUTE_FETCH_MS, fulfill_fetched, open_start_page
from scamworld.env import offsite
from scamworld.env.observation_sync import observe_stable_document, require_document_identity
from scamworld.env.browsergym_adapter import ScamWorldBrowserTask,ScamWorldBrowserEnv,step_reward
from scamworld.scoring.evaluation import load_contract
from scamworld.scoring.outcome import evaluate_episode   # the step reward is score.score's overall
from scamworld.scoring.text_match import text_contains_match
from scamworld.scoring.evaluation.contracts import public_goal,input_policy
from scamworld.scoring.evaluation.observations import accessibility_nodes,accessibility_controls,node_texts
from scamworld.env.transport import resolve_source_transport,navigation_routes
from scamworld.env.image_cues import capture_regions, image_rules, validate_rules, stable_regions

VISIBLE_TEXT_JS=r'''() => {
 const regions=[];const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
 let n;while(n=walker.nextNode()){
  const text=n.textContent.replace(/\s+/g,' ').trim();if(!text||text.length>16000)continue;
  const parent=n.parentElement;if(!parent||parent.closest('script,style,noscript'))continue;
  let painted=true;for(let p=parent;p;p=p.parentElement){const s=getComputedStyle(p);if(s.display==='none'||s.visibility==='hidden'||Number(s.opacity)===0){painted=false;break;}}
  if(!painted)continue;const range=document.createRange();range.selectNodeContents(n);const rects=Array.from(range.getClientRects());
  if(!rects.length||!rects.every(r=>r.width>0&&r.height>0&&r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight))continue;
  if(!rects.every(r=>{const hit=document.elementFromPoint((r.left+r.right)/2,(r.top+r.bottom)/2);return hit&&(hit===parent||parent.contains(hit)||hit.contains(parent));}))continue;
  regions.push({text,rects:rects.map(r=>({x:r.x,y:r.y,width:r.width,height:r.height}))});
 }
 for(const el of document.querySelectorAll('h1,h2,h3,h4,p,label,button,a,li,td')){
  const r=el.getBoundingClientRect(),s=getComputedStyle(el);const text=(el.innerText||'').replace(/\s+/g,' ').trim();
  if(!text||s.display==='none'||s.visibility==='hidden'||Number(s.opacity)===0||r.width<=0||r.height<=0||r.left<0||r.top<0||r.right>innerWidth||r.bottom>innerHeight)continue;
  const hit=document.elementFromPoint((r.left+r.right)/2,(r.top+r.bottom)/2);if(hit&&(hit===el||el.contains(hit)))regions.push({text,rects:[{x:r.x,y:r.y,width:r.width,height:r.height}]});
 }
 return regions;
}'''

# text_contains: raw, else NFKC with all whitespace removed on both sides (scoring/text_match.py)
PRIVATE_ANCHORS_JS=r'''(anchors) => anchors.flatMap(a => {
 const squash=s=>s.normalize('NFKC').replace(/\s+/g,'');
 const matches=Array.from(document.querySelectorAll(a.selector));
 return matches.map(el => {
  const r=el.getBoundingClientRect(),text=(el.innerText||'').replace(/\s+/g,' ').trim();
  let painted=true;for(let p=el;p;p=p.parentElement){const s=getComputedStyle(p);if(s.display==='none'||s.visibility==='hidden'||Number(s.opacity)===0)painted=false;}
  const full=r.width>0&&r.height>0&&r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight;
  const visible=painted&&full&&[[.5,.5],[.05,.05],[.95,.05],[.05,.95],[.95,.95]].every(([x,y])=>{const hit=document.elementFromPoint(r.x+r.width*x,r.y+r.height*y);return hit&&(hit===el||el.contains(hit)||hit.contains(el));});
  const match=!a.text_contains?'':text.includes(a.text_contains)?'raw':(squash(a.text_contains)&&squash(text).includes(squash(a.text_contains)))?'whitespace_insensitive':null;
  return {id:a.id,text,states:a.states||[],rect:{x:r.x,y:r.y,width:r.width,height:r.height},visible:visible&&!!text&&match!==null,...(match?{text_match:match}:{})};
 });
})'''

# Where each anchor's phrase is: [{id, status[, dy]}], status one of SIGN_STATES. An anchor is 'on screen' when the text of
# its element that is on screen contains the phrase, compared without case and with NFKC, then with all whitespace removed.
# A piece of text is on screen when it is painted, every line of it is inside the window, no container cuts it off (a closed
# accordion, a scroll box) and nothing that paints lies over the middle of each line. The piece is the phrase itself where one text node
# holds it, so a long paragraph counts once the lines of the phrase are inside the window; otherwise the whole text node.
# PRIVATE_ANCHORS_JS asks for more: the whole element inside the window and its whole text in one visible block, which a
# table, a list or a box of several lines never is. dy (with 'off screen') is the vertical scroll that would centre the
# phrase in the window.
SIGN_STATES=('missing','text','hidden','off screen','covered','on screen')   # how close the phrase is to being on screen
SIGN_STATE_JS=r"""(anchors) => {
 const norm=s=>s.normalize('NFKC').toLowerCase().replace(/\s+/g,' ').trim(),squash=s=>norm(s).replace(/ /g,'');
 const has=(text,phrase)=>!!text&&(!phrase||norm(text).includes(norm(phrase))||(!!squash(phrase)&&squash(text).includes(squash(phrase))));
 const rank=['text','hidden','off screen','covered','on screen'];
 // Not painted: display none, a closed <details>, content-visibility hidden, visibility hidden (as the element itself has
 // it: a child may switch it back on), or an ancestor with opacity 0.
 const painted=el=>{
  if(el.checkVisibility&&!el.checkVisibility())return false;
  const closed=el.closest('details:not([open])');
  if(closed){const head=closed.querySelector(':scope > summary');if(!head||!head.contains(el))return false;}
  if(['hidden','collapse'].includes(getComputedStyle(el).visibility))return false;
  for(let p=el;p;p=p.parentElement){const s=getComputedStyle(p);if(s.display==='none'||Number(s.opacity)===0)return false;}
  return true;
 };
 // Cut off by an ancestor that hides what overflows it. As CSS has it, such an ancestor cuts a fixed or an absolute element
 // only from its containing block upwards: for both an ancestor with a transform, a filter or containment, for an absolute
 // one also any positioned ancestor. A line may stick out by a quarter of its height (tight line boxes).
 const cuts=v=>['hidden','clip','scroll','auto'].includes(v);
 const holds=s=>s.transform!=='none'||s.perspective!=='none'||s.filter!=='none'||(s.backdropFilter||'none')!=='none'
  ||/paint|layout|strict|content/.test(s.contain||'')||/transform|perspective|filter/.test(s.willChange||'');
 const cut=(rects,el)=>{
  let free=null;
  for(let p=el;p&&p!==document.body&&p!==document.documentElement;p=p.parentElement){
   const s=getComputedStyle(p);
   if(free&&(holds(s)||(free==='absolute'&&s.position!=='static')))free=null;
   if(!free&&s.display!=='inline'&&s.display!=='contents'&&(cuts(s.overflowX)||cuts(s.overflowY))){
    const q=p.getBoundingClientRect(),left=q.left+p.clientLeft,top=q.top+p.clientTop,right=left+p.clientWidth,bottom=top+p.clientHeight;
    if(rects.some(r=>{const ty=Math.max(2,r.height/4);
     return (cuts(s.overflowX)&&(r.left<left-2||r.right>right+2))||(cuts(s.overflowY)&&(r.top<top-ty||r.bottom>bottom+ty));}))return true;
   }
   const clip=['absolute','fixed'].includes(s.position)&&/^rect\((.+)\)$/.exec(s.clip||'');   // clip: rect(top, right, bottom, left) from the box's own corner
   if(clip){
    const q=p.getBoundingClientRect(),[t,r,b,l]=clip[1].split(/[\s,]+/).filter(Boolean).map(parseFloat);
    const left=q.left+(isNaN(l)?0:l),top=q.top+(isNaN(t)?0:t),right=q.left+(isNaN(r)?q.width:r),bottom=q.top+(isNaN(b)?q.height:b);
    if(rects.some(c=>c.left<left-2||c.right>right+2||c.top<top-2||c.bottom>bottom+2))return true;
   }
   if(s.position==='fixed')free='fixed';else if(s.position==='absolute'&&free!=='fixed')free='absolute';
  }
  return false;
 };
 // Covered. What paints is a background colour that is not fully transparent, a background image or a backdrop filter; an
 // image, a video, a frame and an SVG shape always do. An element over the text that paints nothing (a link stretched over a
 // card, an overlay with opacity 0) is looked through. Not seen: paint that takes no pointer events (an overlay with
 // pointer-events none, a box shadow, an outline) and a border.
 const alpha=c=>{
  if(!c||c==='transparent')return 0;
  const m=/^rgba?\((.+)\)$/.exec(c),other=/\/\s*([\d.]+)(%?)\s*\)$/.exec(c);   // another colour function has its alpha after a slash
  if(m){const v=m[1].split(/[\s,\/]+/).filter(Boolean);return v.length>3?parseFloat(v[3]):1;}
  return other?parseFloat(other[1])/(other[2]?100:1):1;
 };
 const fills=s=>s.visibility!=='hidden'&&Number(s.opacity)!==0&&(alpha(s.backgroundColor)>0||s.backgroundImage!=='none'||(s.backdropFilter||'none')!=='none');
 const solid=el=>/^(img|video|canvas|iframe|object|embed)$/.test(el.localName)||(el instanceof SVGElement&&el.localName!=='svg')||fills(getComputedStyle(el));
 const is=(el,selector)=>{try{return el.matches(selector);}catch(e){return false;}};
 // The ::backdrop of an open modal dialog, popover or fullscreen element lies over the rest of the page.
 const backdrop=el=>(is(el,':modal')||is(el,':popover-open')||is(el,':fullscreen'))&&fills(getComputedStyle(el,'::backdrop'));
 const shown=el=>{for(let p=el;p;p=p.parentElement){if(Number(getComputedStyle(p).opacity)===0)return false;}return true;};
 const boxAt=(el,x,y)=>Array.from(el.getClientRects()).some(r=>x>=r.left&&x<=r.right&&y>=r.top&&y<=r.bottom);
 const behind=(el,ancestor)=>{for(let p=el;p&&p!==ancestor;p=p.parentElement){if(parseInt(getComputedStyle(p).zIndex)<0)return true;}return false;};
 const px=v=>/px$/.test(v||'')?parseFloat(v):null;
 // The corner that an absolute ::before or ::after of `el` is placed from, and the scale of what is placed there: the padding
 // box of `el` or of its nearest ancestor that is positioned or holds (above); the window for a fixed one.
 const corner=(el,fixed)=>{
  for(let c=el;c&&c!==document.documentElement;c=c.parentElement){
   const s=getComputedStyle(c);
   if(holds(s)||(!fixed&&s.position!=='static')){
    const q=c.getBoundingClientRect(),sx=c.offsetWidth?q.width/c.offsetWidth:1,sy=c.offsetHeight?q.height/c.offsetHeight:1;
    return {left:q.left+(c.clientLeft-c.scrollLeft)*sx,top:q.top+(c.clientTop-c.scrollTop)*sy,sx,sy};
   }
  }
  return fixed?{left:0,top:0,sx:1,sy:1}:{left:-scrollX,top:-scrollY,sx:1,sy:1};
 };
 // A rotation, a skew or a 3D transform on the element or above it.
 const turned=el=>{
  for(let p=el;p;p=p.parentElement){
   const s=getComputedStyle(p),m=/^matrix\((.+)\)$/.exec(s.transform);
   if((s.rotate&&s.rotate!=='none')||(s.transform!=='none'&&(!m||m[1].split(',').slice(1,3).some(Number))))return true;
  }
  return false;
 };
 // A ::before or ::after of `el` that paints and lies over the point: placed absolute or fixed, not behind the text (z-index
 // below 0), its box taken from the used values the browser gives, scaled and moved by its transform. A box that cannot be
 // worked out (a rotation here or above, the scale, rotate or translate property) counts as lying over the point.
 const veils=(el,x,y)=>['::before','::after'].some(part=>{
  const s=getComputedStyle(el,part);
  if(s.content==='none'||s.content==='normal'||s.display==='none'||!['absolute','fixed'].includes(s.position)||parseInt(s.zIndex)<0||!fills(s))return false;
  let x0=px(s.left),y0=px(s.top);const width=px(s.width),height=px(s.height);
  if([x0,y0,width,height].includes(null)||['scale','rotate','translate'].some(k=>s[k]&&s[k]!=='none')||turned(el))return true;
  let x1=x0+width,y1=y0+height;
  if(s.transform!=='none'){
   const m=/^matrix\((.+)\)$/.exec(s.transform),v=m?m[1].split(',').map(Number):[],o=(s.transformOrigin||'').split(' ').map(parseFloat);
   if(v.length!==6||v[1]||v[2]||o.length<2||o.some(isNaN))return true;
   const cx=x0+o[0],cy=y0+o[1];
   [x0,x1]=[cx+(x0-cx)*v[0]+v[4],cx+(x1-cx)*v[0]+v[4]].sort((a,b)=>a-b);[y0,y1]=[cy+(y0-cy)*v[3]+v[5],cy+(y1-cy)*v[3]+v[5]].sort((a,b)=>a-b);
  }
  const from=corner(el,s.position==='fixed');
  return x>=from.left+x0*from.sx&&x<=from.left+x1*from.sx&&y>=from.top+y0*from.sy&&y<=from.top+y1*from.sy;
 });
 // Nothing that paints lies over the text of `parent` at the point. elementsFromPoint lists what is there from the top down;
 // an ancestor listed above `parent` is there with a ::before or ::after, or `parent` lies behind it (z-index below 0).
 // `parent` is not listed when it takes no pointer events or its text sticks out of its box: then the text counts once an
 // ancestor is reached with nothing that paints above it.
 const onTop=(parent,x,y)=>{
  const stack=document.elementsFromPoint(x,y),listed=stack.includes(parent);
  for(const el of stack){
   if(el===parent)return !veils(el,x,y);
   if(el.contains(parent)){
    if(veils(el,x,y))return false;
    if(!listed)return true;
    if(el!==document.body&&el!==document.documentElement&&behind(parent,el)&&boxAt(el,x,y)&&fills(getComputedStyle(el)))return false;
   }else if(shown(el)&&((boxAt(el,x,y)&&solid(el))||veils(el,x,y)||backdrop(el)))return false;
  }
  return false;
 };
 const stateOf=(all,parent)=>{
  const rects=all.filter(r=>r.width>0&&r.height>0);   // a line break kept by the page (pre) gives a rect without width
  if(!rects.length||cut(rects,parent))return 'hidden';
  if(!rects.every(r=>r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight))return 'off screen';
  return rects.every(r=>onTop(parent,(r.left+r.right)/2,(r.top+r.bottom)/2))?'on screen':'covered';
 };
 const rectsOf=(n,start,end)=>{const range=document.createRange();if(start===undefined)range.selectNodeContents(n);else{range.setStart(n,start);range.setEnd(n,end);}return Array.from(range.getClientRects());};
 // The places of the phrase inside one text node (spaces in the phrase stand for any run of whitespace); [] when the node
 // does not hold the whole phrase as written.
 const places=(raw,phrase)=>{
  const words=phrase.trim().split(/\s+/).filter(Boolean).map(w=>w.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'));
  if(!words.length)return [];
  let re;try{re=new RegExp(words.join('\\s+'),'giu');}catch(e){return [];}
  const found=[];let m;
  while((m=re.exec(raw))&&found.length<20){found.push([m.index,m.index+m[0].length]);if(!m[0].length)re.lastIndex++;}
  return found;
 };
 const nodes=(el,phrase)=>{
  const out=[],walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);let n;
  while(n=walker.nextNode()){
   const text=n.textContent.replace(/\s+/g,' ').trim(),parent=n.parentElement;
   if(!text||!parent||parent.closest('script,style,noscript'))continue;
   let best=null;
   if(!painted(parent))best={state:'hidden',rects:[]};
   else for(const rects of [...places(n.textContent,phrase).map(([a,b])=>rectsOf(n,a,b)),rectsOf(n)]){
    const state=stateOf(rects,parent);
    if(!best||rank.indexOf(state)>rank.indexOf(best.state))best={state,rects};
    if(state==='on screen')break;
   }
   out.push({text,state:best.state,top:Math.min(...best.rects.map(r=>r.top),Infinity),bottom:Math.max(...best.rects.map(r=>r.bottom),-Infinity)});
  }
  return out;
 };
 return anchors.map(a=>{
  let els=[];try{els=Array.from(document.querySelectorAll(a.selector));}catch(e){}
  let best={id:a.id,status:'missing'};
  const phrase=a.text_contains==null?'':String(a.text_contains);
  for(const el of els){
   let all;try{all=nodes(el,phrase);}catch(e){continue;}
   const within=level=>all.filter(n=>rank.indexOf(n.state)>=rank.indexOf(level));
   const level=['on screen','covered','off screen','hidden'].find(l=>has(within(l).map(n=>n.text).join(' '),phrase))||'text';
   if(best.status!=='missing'&&rank.indexOf(level)<=rank.indexOf(best.status))continue;
   best={id:a.id,status:level};
   if(level==='off screen'){
    const away=within('off screen').filter(n=>n.state==='off screen'),own=away.filter(n=>has(n.text,phrase));
    const pick=own.length?own:away,top=Math.min(...pick.map(n=>n.top)),bottom=Math.max(...pick.map(n=>n.bottom));
    if(isFinite(top)&&isFinite(bottom))best.dy=Math.round((top+bottom)/2-innerHeight/2);
   }
  }
  return best;
 });
}"""

class FormalRuntime(BrowserRuntime):
 def __init__(self,*args,logical_url=None,private_anchors=None,local_navigation_routes=None,private_image_cues=None,**kwargs):
  self.private_image_cues=validate_rules(args[0] if args else kwargs['site_dir'],private_image_cues)
  self.input_policy=input_policy()
  super().__init__(*args,**kwargs);self.logical_url=logical_url;self.private_anchors=[a for a in (private_anchors or []) if a.get('type')!='observed_url']
  self.local_navigation_routes = {r['url']:r['local_path'] for r in navigation_routes(local_navigation_routes)} if local_navigation_routes is not None else {}
  self.logical_origin=None
  if logical_url:
   parsed=urlparse(logical_url)
   if parsed.scheme not in ['http','https'] or not parsed.hostname:raise ValueError('Invalid source URL')
   self.logical_origin=parsed.scheme+'://'+parsed.netloc.lower()
 def _state(self):
  state=super()._state()
  if not state['state_id']:
   parsed=urlparse(self.page.url)
   state['state_id']='source:'+ (parsed.path or '/')+('#'+parsed.fragment if parsed.fragment else '')
  state['session_storage']=self.page.evaluate('(()=>{try{return Object.fromEntries(Object.entries(sessionStorage))}catch(e){return {}}})()')   # opaque origin: no storage
  return state
 def _allowed(self,url):
  parsed=urlparse(url)
  return url in self.local_navigation_routes or bool(self.logical_origin and parsed.scheme+'://'+parsed.netloc.lower()==self.logical_origin) or super()._allowed(url)
 def _route(self,route):
  if self._route_offsite(route):return   # experiment option offsite (env/offsite.py); off by default
  request=route.request;parsed=urlparse(request.url)
  if request.url in self.local_navigation_routes and request.method in ['GET','HEAD'] and request.is_navigation_request() and request.frame == self.page.main_frame:
   response=route.fetch(url=self.server.origin+self.local_navigation_routes[request.url],max_redirects=0,timeout=ROUTE_FETCH_MS)
   self._fulfill_local(route,response)   # a context closed meanwhile: _guarded_route drops the error (detach)
  elif self.logical_origin and parsed.scheme+'://'+parsed.netloc.lower()==self.logical_origin and request.method in ['GET','HEAD']:
   response=route.fetch(url=self.server.origin+parsed.path+('?' + parsed.query if parsed.query else ''),max_redirects=0,timeout=ROUTE_FETCH_MS)
   self._fulfill_local(route,response)
  elif super()._allowed(request.url) and request.method in ['GET','HEAD']:
   route.continue_()
  else:
   self._refuse(route)   # a top-level navigation shows the unreachable page (runtime.BrowserRuntime._refuse)
 def _fulfill_local(self,route,response):
  # A redirect of the local server (a directory without its slash: 301 to path/) is never handed to the
  # browser, which would follow it outside the route handler, to the live site of the logical domain
  refused=fulfill_fetched(route,response)
  if refused:self.events.append({'type':'boundary_attempt','url':refused,'method':route.request.method,'transport':'redirect','blocked':True,'step':len(self.actions)+1})
 def attach(self,page):
  if not self.logical_origin:return super().attach(page)
  self.page,self.context=page,page.context
  self._closing=False
  self.context.route('**/*',self._guarded_route)
  self.context.on('response',self._not_found)   # records the 404s of a logical origin
  guard=GUARD_JS.replace('new URL(u,location.href).origin===origin', 'new URL(u,location.href).origin===origin || '+json.dumps(list(self.local_navigation_routes))+'.includes(new URL(u,location.href).href)') if self.local_navigation_routes else GUARD_JS
  self.context.add_init_script(offsite.init_script(guard,self.logical_origin))
  self.page.on('dialog',lambda dialog:dialog.dismiss())
  self.page.on('pageerror',lambda error:self.environment_errors.append({'type':'pageerror','message':str(error)}))
  self.context.on('page',self._new_page)
  self.page.on('download',lambda download:download.cancel())
 def reset(self,*,seed=0):
  # Native calibration uses the same local-backed logical origin as BrowserGym.
  public,info=super().reset(seed=seed)
  if self.logical_url:
   self.start_page_wait=open_start_page(self.page,self.logical_origin+self.start_path)
   self.observations=[];self.actions=[];self.events=[];self.environment_errors=[]
   public=self.observe()
  return public,info
 def sign_states(self,state_id):
  """SIGN_STATE_JS on the page as it is now, for the anchors that apply in the task state `state_id`."""
  return self.page.evaluate(SIGN_STATE_JS,[{'id':a['id'],'selector':to_served(a['selector']),'text_contains':a.get('text_contains')}
                                           for a in self.private_anchors if a.get('selector') and (not a.get('states') or state_id in a['states'])])
 def observe(self):
  images_before=capture_regions(self.context,self.page,self.private_image_cues) if self.private_image_cues else []
  public=super().observe()
  record=self.observations[-1];record['visible_text_regions']=self.page.evaluate(VISIBLE_TEXT_JS)
  # Add full region anchors only when the same captured viewport exposes them.
  record['visible_text_regions'] += [{'text':e['text'],'anchor_id':e['evidence_id'],'rects':[e['viewport_bbox']]} for e in record['visible_evidence']]
  # Private selector readback never tags or changes the website DOM. IDs stay
  # in evaluator artifacts; the public observation remains screenshot/controls.
  anchors=self.page.evaluate(PRIVATE_ANCHORS_JS,[{**a,'selector':to_served(a['selector'])} for a in self.private_anchors])   # the names served to the page
  state=record['state']['state_id']
  visible_text=[' '.join(r['text'].split()).casefold() for r in record['visible_text_regions']]
  record['private_anchor_regions']=[a for a in anchors if a['visible'] and (not a['states'] or state in a['states']) and any(' '.join(a['text'].split()).casefold() in text for text in visible_text)]
  # The anchors whose phrase is on screen inside their own element (SIGN_STATE_JS), for Episode.signs_seen() and `scamworld
  # signs`. A list of its own: nothing that scoring reads (private_anchor_regions, visible_text_regions) changes with it,
  # and a failure here leaves the step without the list (older traces have none either) rather than ending the episode.
  try:record['signs_on_screen']=[s['id'] for s in self.sign_states(state) if s['status']=='on screen']
  except Exception as error:record['signs_on_screen_error']=f'{type(error).__name__}: {error}'[:300]
  if self.private_image_cues:
   # Verify local asset bytes again at capture time, then require stable source
   # and geometry around the actual screenshot. Never infer a logo from alt text.
   validate_rules(self.site_dir,self.private_image_cues)
   images_after=capture_regions(self.context,self.page,self.private_image_cues)
   record['image_cue_regions']=stable_regions(images_before,images_after,self.private_image_cues,allowed_url=self._allowed,observation_id=record['observation_id'],screenshot_sha256=record['screenshot_sha256'],screenshot_path=record['screenshot_path'])
  self._save();return public
 def record_public_accessibility(self,obs):
  """Record exactly the accessibility projection that public_obs supplies."""
  import copy
  # Assemble privately; do not publish/save mixed AX fields before identity validation.
  record=copy.deepcopy(self.observations[-1])
  if obs.get('step_id')!=record['step_id'] or obs.get('observation_id')!=record['observation_id']:raise RuntimeError('Accessibility observation identity mismatch')
  all_nodes=obs.get('axtree_object',{}).get('nodes',[]);provided=accessibility_nodes(obs)
  if not isinstance(obs.get('url'),str):raise RuntimeError('Public observation URL is unavailable')
  record['public_url']=obs['url']
  record['public_accessibility_controls']=copy.deepcopy(accessibility_controls(obs))
  record['public_accessibility_nodes']=copy.deepcopy(provided)
  record['accessibility_tree_links']=[{'node_id':str(n.get('nodeId')),'child_ids':[str(c) for c in n.get('childIds',[])],'backend_dom_node_id':n.get('backendDOMNodeId')} for n in all_nodes]
  record['public_accessibility_text']=[{'text':text,'node_id':str(node.get('nodeId'))} for node in provided for text in node_texts(node)]
  record['accessibility_text_evidence']={};record['accessibility_anchor_nodes']={}
  if all_nodes and self.private_anchors:
   indexed={str(node['nodeId']):node for node in all_nodes if 'nodeId' in node};provided_ids={str(n.get('nodeId')) for n in provided}
   session=self.context.new_cdp_session(self.page)
   try:
    document=session.send('DOM.getDocument',{'depth':0})['root']['nodeId']
    for anchor in self.private_anchors:
     if anchor.get('states') and record['state']['state_id'] not in anchor['states']:continue
     dom_ids=session.send('DOM.querySelectorAll',{'nodeId':document,'selector':to_served(anchor['selector'])})['nodeIds']
     backends={session.send('DOM.describeNode',{'nodeId':node})['node']['backendNodeId'] for node in dom_ids}
     roots=[str(n['nodeId']) for n in all_nodes if n.get('backendDOMNodeId') in backends]
     selected=[];seen=set();pending=list(roots);texts=[]
     while pending:
      node_id=pending.pop(0)
      if node_id in seen:continue
      seen.add(node_id);node=indexed.get(node_id)
      if node is None:continue
      if node_id in provided_ids:
       selected.append(node);values=node_texts(node)
       if values:
        texts += values
        # Named accessible nodes already supply this text; descendant inline
        # boxes duplicate it. Preserve sibling order instead of duplicating it.
        continue
      pending = [str(child) for child in node.get('childIds',[])] + pending
     text=' '.join(''.join(texts).split())
     needle=anchor.get('text_contains');hit=text_contains_match(text,needle) if needle else None
     if text and (not needle or hit):
      record['accessibility_text_evidence'][anchor['id']]=text
      record['accessibility_anchor_nodes'][anchor['id']]=[str(node['nodeId']) for node in selected]
      if hit:record.setdefault('accessibility_text_match',{})[anchor['id']]=hit
   finally:session.detach()
  require_document_identity(self,record.get('document_identity'),'public accessibility evidence capture')
  self.observations[-1]=record
  self._save()
 def export_trace(self):
  trace=super().export_trace()
  for step in trace['steps']:
   source=next(o for o in self.observations if o['step_id']==step['step_id'])
   step['observation']['visible_text_regions']=source.get('visible_text_regions',[])
   step['observation'].setdefault('visible_text_evidence',{}).update({a['id']:a['text'] for a in source.get('private_anchor_regions',[])})
   matched={a['id']:a['text_match'] for a in source.get('private_anchor_regions',[]) if a.get('text_match')}
   if matched:step['observation'].setdefault('visible_text_match',{}).update(matched)   # how text_contains matched
   for key in ('signs_on_screen','signs_on_screen_error'):   # on the step itself: scoring searches step['observation'] as text
    if key in source:step[key]=source[key]
   for key in ['public_url','public_accessibility_controls','public_accessibility_nodes','accessibility_tree_links','public_accessibility_text','accessibility_text_evidence','accessibility_anchor_nodes','accessibility_text_match','agent_controls_dropped','agent_controls_chars']:   # agent_controls_*: episode.note_agent_controls
    if key in source:step['observation'][key]=source[key]
   if 'image_cue_regions' in source:step['observation']['image_cue_regions']=source['image_cue_regions']
  if getattr(self,'transport_adaptation',None):trace['transport_adaptation']=self.transport_adaptation
  if getattr(self,'leave_site_ends',True) is False:trace['leave_site_ends']=False   # a11: leaving the site does not end the episode
  trace['input_policy']=self.input_policy
  trace['task_contract_version']='0.2.1';return trace

class FormalBrowserTask(ScamWorldBrowserTask):
 final_reply='message'   # a11: the agent's message to the user is the final answer, {"message": text}
 def __init__(self,seed,*,case_dir,artifact_dir,goal=None,task_path=None,overlay=None,final_reply='message'):
  if final_reply not in ('message','structured'):raise ValueError('final_reply is message or structured')
  self.final_reply=final_reply   # structured: the legacy protocol's JSON answer (episode.run_one)
  if task_path is not None and goal is not None:raise ValueError('External tasks cannot use an unreviewed goal override')
  if overlay is not None and goal is not None:raise ValueError('A task overlay carries its own instruction; no goal override')
  folder=Path(case_dir).resolve();contract=load_contract(folder,task_path=task_path,overlay=overlay)
  from scamworld.scoring.cue_sets import load_interface
  interface=load_interface(contract,(contract['evaluation'].get('case_scoring') or {}).get('reason_rubric') or {})
  super().__init__(seed,site_dir=folder/'site',artifact_dir=artifact_dir,case_id=contract['task']['case_id'],goal=public_goal(contract['task'],goal),case=contract,evaluator=evaluate_episode,start_path=contract['task'].get('start_path','/index.html'))
  self.runtime.server.close()
  provenance=json.loads((folder/'source/provenance.json').read_text());logical_url,transport=resolve_source_transport(provenance,contract['evaluation'])
  from scamworld.corpus.dead_links_a6e import unavailable   # served paths the site answers 404 (records/a6e-dead-links.json)
  self.runtime=FormalRuntime(folder/'site',artifact_dir,case_id=contract['task']['case_id'],start_path=contract['task'].get('start_path','/index.html'),logical_url=logical_url,private_anchors=contract['evaluation'].get('anchors',[]),local_navigation_routes=(transport or {}).get('navigation_routes'),private_image_cues=image_rules(interface),unavailable=unavailable(folder))
  self.runtime.transport_adaptation=transport
  # Under a11, with a free-text final message, leaving the site does not end the
  # episode (the agent must be able to write its message); the trace says so, and the scorer then reads the outcome from the
  # state and the message (score.score_v2 / score_asked). Recorded traces lack the key: leaving ended them.
  self.runtime.leave_site_ends=final_reply!='message'
  self.offsite_notice=False
  from scamworld.agents import url_visibility
  if url_visibility.hidden():self.goal=url_visibility.scrub_goal(self.goal,logical_url)   # no site host in the goal
  self.runtime.seed=seed;self.runtime.episode_id=1
 def setup(self,page):
  self.runtime.attach(page)
  self.runtime.start_page_wait=open_start_page(page,(self.runtime.logical_origin or self.runtime.server.origin)+self.runtime.start_path)
  _,self.previous_state=observe_stable_document(self.runtime,[])
  return self.goal,{'case_id':self.runtime.case_id,'network_policy':'source-origin URLs locally fulfilled; no external website request'}
 def validate(self,page,chat_messages):
  messages=chat_messages[self.last_chat_length:]
  for message in messages:
   if message.get('role')=='assistant' and self.final_reply=='message':
    answer={'message':str(message.get('message',''))}
    self.runtime.final_answer=answer;self.runtime.terminated=True
    self.pending_normalized_action={'type':'final_answer','value':answer}
   elif message.get('role')=='assistant':
    try:
     answer=json.loads(message.get('message',''))
     if isinstance(answer,dict):
      self.runtime.final_answer=answer;self.runtime.terminated=True
      self.pending_normalized_action={'type':'final_answer','value':answer}
    except (TypeError,json.JSONDecodeError):pass
  self.offsite_notice=False
  result=super().validate(page,chat_messages)
  # The episode ends as soon as the agent takes the task's final action (<prefix>.risk_commit: the risky action on a scam
  # site, the completed task on a legitimate one); under the older protocol (leave_site_ends) it also ends when the agent
  # leaves the site to verify elsewhere. Cases opt in by listing evaluation.terminal_event_ids; cases without the list do
  # not end on these events.
  terminal=set(self.case['evaluation'].get('terminal_event_ids',[]))
  if not self.runtime.leave_site_ends:
   # a11: an off-site link (pagekit leave_links: the click is kept on the page and <prefix>.leave_site recorded) is answered as
   # a typed off-site address is (action_errors.UNREACHABLE) and the episode goes on to the agent's own finish. No task commits
   # through an off-site link: every leave_site is consequence "left_site_to_verify"; an off-site link that commits carries
   # data-dx-do and emits <prefix>.risk_commit, which still ends the episode.
   terminal={t for t in terminal if not t.endswith('.leave_site')}
   last=self.runtime.actions[-1] if self.runtime.actions else {}
   if not self.runtime.terminated and any(str(e.get('event_id') or '').endswith('.leave_site') for e in last.get('events',[])):
    from scamworld.env.action_errors import UNREACHABLE
    last['error']=UNREACHABLE;self.offsite_notice=True;self.runtime._save()
  if terminal and not self.runtime.terminated and self.runtime.actions:
   # match site events by event_id; 'boundary_attempt' (blocked off-site navigation = left to verify) by type
   hit=[e.get('event_id') or e.get('type') for e in self.runtime.actions[-1].get('events',[]) if e.get('event_id') in terminal or e.get('type') in terminal]
   if hit:
    self.runtime.terminated=True;self.runtime._save()
    _,_,message,info=result
    ev=self.evaluator(self.case,self.runtime.export_trace())   # offline (no judge), as a finish is evaluated
    info=dict(info,scoring_status='evaluated',evaluation=ev,terminated_by_event=hit[0])
    return step_reward(ev),True,message,info
  return result
 def teardown(self):
  trace=self.runtime.export_trace();result=evaluate_episode(self.case,trace)
  (self.runtime.artifact_dir/'evaluation.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
  (self.runtime.artifact_dir/'trace.json').write_text(json.dumps(trace,indent=2,ensure_ascii=False)+'\n')
  super().teardown()

# BrowserGym core frame_mark_elements.js writes current value/checked to source
# attributes during observation. Preserve source reset defaults independently of
# the extracted AX values. The reset listener covers a source timer firing while
# extraction is in progress; it restores defaults before native form reset.
BEGIN_OBSERVATION_DEFAULTS_JS = r"""() => {
 const entries=Array.from(document.querySelectorAll('input')).map(el=>({el,
  value:el.getAttribute('value'),checked:el.getAttribute('checked')}));
 const restore=(preserveCurrent)=>{
  for(const {el,value,checked} of entries){
   if(!el.isConnected)continue;
   const currentValue=el.value,currentChecked=el.checked;
   if(value===null)el.removeAttribute('value');else el.setAttribute('value',value);
   if(checked===null)el.removeAttribute('checked');else el.setAttribute('checked',checked);
   if(preserveCurrent){if(el.type!=='file' && el.value!==currentValue)el.value=currentValue;if(el.checked!==currentChecked)el.checked=currentChecked;}
  }
 };
 const onReset=()=>restore(false);
 document.addEventListener('reset',onReset,true);
 window.__pagekitEndObservationDefaults=()=>{
  document.removeEventListener('reset',onReset,true);restore(true);
  delete window.__pagekitEndObservationDefaults;
 };
}"""
END_OBSERVATION_DEFAULTS_JS = r"""() => {
 if(window.__pagekitEndObservationDefaults)window.__pagekitEndObservationDefaults();
}"""

class FormalBrowserEnv(ScamWorldBrowserEnv):
 def _get_obs(self):
  from playwright.sync_api import Error as PlaywrightError
  frames=[]
  for frame in self.page.frames:
   if not frame.is_detached():
    frame.evaluate(BEGIN_OBSERVATION_DEFAULTS_JS);frames.append((frame,frame.url))
  try:
   obs=super()._get_obs()
  finally:
   for frame,url in frames:
    try:frame.evaluate(END_OBSERVATION_DEFAULTS_JS)
    except PlaywrightError:
     if not frame.is_detached() and frame.url==url:raise
  if self.task.case['task'].get('citation_scope','screenshot')=='accessibility' and 'axtree_object' not in obs:raise ValueError('Accessibility citation scope requires supplied AX observations')
  self.task.runtime.record_public_accessibility(obs)
  return obs
