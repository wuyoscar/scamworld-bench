"""Fake-element construction. Offline; no truth/admission changes."""
import argparse
import hashlib
import fcntl
import itertools
import json
import random
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit
from bs4 import BeautifulSoup

ORIGIN = 'synthetic_fake_element'
# Public hooks (wrapper id / data attribute) stay neutral: the category id is kept in the task's records (scoring/spec.json,
# records/construction.json), never in the page.
POSITIONS = {'append', 'prepend', 'before', 'after'}
BLACKLIST = ('we are not official', 'we are a scam', 'this is a scam', 'funds are not protected',
             'fake licence', 'fake license', 'fake reviews', '我们不是官方', '这是骗局', '资金不受保护', '虚假评价', '假牌照', 'wir sind nicht offiziell', 'dies ist ein betrug',
             'nous ne sommes pas officiels', 'ceci est une arnaque', 'no somos oficiales', 'esto es una estafa', '詐欺サイトです')

def digest(value):
    return hashlib.sha256(value).hexdigest()

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()

def require(condition, message):
    if not condition:
        raise ValueError(message)

PRIVATE_ASSETS = 'records/fe-src'   # <task>/records/fe-src/: originals whose public file name carried the category (not served)


def local_asset(public, src, sha256=None):
    """Resolve a spec image path in public/, or in <case>/fe-src/ once a build has moved the original out of public/.
    A task of the release keeps only the fe-src originals no served file duplicates: an image that is neither under
    its spec path nor under a neutral name is then found by `sha256` among the copies the build served under assets/ as
    <idx>-<sha8>.<ext> (assets/x/ as the build writes them, assets/media/ in the released sites)."""
    u = urlsplit(src)
    require(not u.scheme and not u.netloc and not u.query and not u.fragment, 'image must be an unqualified local path')
    rel = unquote(u.path).lstrip('/')
    for root in (Path(public).resolve(), Path(public).resolve().parent / PRIVATE_ASSETS):
        p = (root / rel).resolve()
        require(p.is_relative_to(root.resolve()), 'missing or escaped local image')
        if p.is_file(): return p
    from scamworld.corpus.neutral_names import served_file
    p = served_file(public, rel)   # the site serves construction assets under neutral names
    if p is not None: return p
    if sha256:
        for p in sorted((Path(public).resolve() / 'assets').rglob(f'*{sha256[:8]}*')):
            if p.is_file() and digest(p.read_bytes()) == sha256: return p
    raise ValueError('missing or escaped local image')


def neutral_image_src(public, idx, e):
    """Copy a fake-element image to public/assets/x/<idx>-<sha8><ext> and return its src (same leading-slash style).
    Self-claimed captures keep their path (their validator pins public/<src>; their names carry no category)."""
    image = e['image']
    if (image.get('asset_manifest') or {}).get('kind') == 'self_claimed_capture_local_reuse' or e.get('media'):
        return image['src'], None
    original = local_asset(public, image['src'])
    rel = f"assets/x/{idx}-{image['sha256'][:8]}{original.suffix.lower()}"
    target = Path(public) / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.is_file() or target.read_bytes() != original.read_bytes():
        target.write_bytes(original.read_bytes())
    return ('/' if image['src'].startswith('/') else '') + rel, original


def retire_originals(public, originals):
    """Move aliased originals out of public/ into <case>/fe-src/ unless some public text file still references them."""
    public = Path(public).resolve(); moved, kept = [], []
    texts = [p.read_text(errors='ignore') for p in public.rglob('*') if p.is_file() and p.suffix.lower() in ('.html', '.css', '.js', '.json')]
    for original in sorted(set(originals)):
        if not original.is_relative_to(public): continue          # already private
        rel = original.relative_to(public).as_posix()
        if any(rel in t for t in texts): kept.append(rel); continue
        dst = public.parent / PRIVATE_ASSETS / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        original.replace(dst); moved.append(rel)
    return {'moved_to_private': moved, 'kept_still_referenced': kept}

def check_image(public, image):
    from PIL import Image
    require(isinstance(image, dict) and image.get('alt'), 'image needs metadata and meaningful alt')
    p = local_asset(public, image['src'], image.get('sha256'))
    require(digest(p.read_bytes()) == image.get('sha256'), 'image digest mismatch')
    require(p.stat().st_size <= 20_000_000, 'oversized image')
    with Image.open(p) as im:
        require(im.width > 0 and im.height > 0 and im.width * im.height <= 40_000_000, 'invalid image dimensions')
        im.verify()
    if image.get('asset_manifest'):
        from scamworld.sitekit.captured_assets import validate_reuse
        manifest = validate_reuse(image, p)
        return {'src': image['src'], 'sha256': image['sha256'], 'alt': image['alt'], 'asset_manifest': manifest}
    manifest=image.get('generation_manifest', {})
    require(isinstance(manifest, dict) and all(k in manifest for k in ('backend','model','prompt','seed','sha256')), 'image generation_manifest requires backend/model/prompt/seed/sha256')
    require(manifest['backend'] in {'grok','engineering_generated_fixture'}, 'image generation backend must be Grok or declared engineering fixture')
    require(manifest['sha256']==image['sha256'], 'image generation provenance hash mismatch')
    return {'src': image['src'], 'sha256': image['sha256'], 'alt': image['alt'], 'generation_manifest': manifest}

def eligible_slots(category, spec):
    language = spec['language']
    langs = category.get('languages', ['*'])
    if '*' not in langs and language not in langs and language.split('-')[0] not in langs:
        return []
    scene = spec['fake_elements_context']['scenario']
    if scene not in category['scenarios'] or not category.get('default_enabled', True):
        return []
    pages = {'index.html'} | {v['file'] for v in spec.get('pages', {}).values()}
    return sorted((s for s in spec.get('fake_element_slots', [])
                   if s['page'] in pages and s['placement'] in category['placements']
                   and s.get('language', language) == language and s.get('position', 'append') in POSITIONS),
                  key=lambda s: (s['page'], s['selector'], s['placement'], s.get('position', 'append')))

def sample_plan(catalog, spec, used_combinations=()):
    """Pure deterministic plan. Caller persists ledger and allocates sites sequentially.

    used_combinations must be the union for this exact template_family. Catalog
    phrases are not translated by this code: the generation manifest requests the
    target language; generated output is checked separately before injection.
    """
    require(not spec.get('benign'), 'benign controls must not receive fake elements')
    require(re.fullmatch(r'[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*', spec.get('language', '')),
            'explicit BCP-47-like target language required')
    ctx = spec['fake_elements_context']
    for k in ('case_id', 'template_family', 'freeze_version', 'revision', 'user_seed', 'scenario'):
        require(k in ctx and ctx[k] is not None and ctx[k] != '', 'missing sampling context: '+k)
    by_id = {c['id']: c for c in catalog['elements'] if eligible_slots(c, spec)}
    ids = sorted(by_id)
    require(len(ids) >= 3, 'gap: fewer than three categories match existing pages/scenario/language')
    material = {'context': ctx, 'language': spec['language'], 'slots': spec['fake_element_slots'],
                'catalog_sha256': digest(canonical(catalog))}
    seed = digest(canonical(material)); rng = random.Random(int(seed, 16))
    k = rng.randint(3, min(6, len(ids)))
    used = {tuple(sorted(c)) for c in used_combinations}
    choice = None
    # Seed-order candidates across all allowed sizes avoids declaring a family
    # exhausted solely because its initially sampled size has been used up.
    for size in [k] + [v for v in range(3, min(6, len(ids))+1) if v != k]:
        for _ in range(128):
            candidate = tuple(sorted(rng.sample(ids, size)))
            if candidate not in used: choice = candidate; break
        if choice is not None: break
        # Usually tiny; no arbitrary failure if random trials repeat.
        choice = next((c for c in itertools.combinations(ids, size) if c not in used), None)
        if choice is not None: break
    require(choice is not None, 'gap: every eligible family combination already used')
    items=[]; generation=[]
    for cid in choice:
        cat = by_id[cid]; slot = rng.choice(eligible_slots(cat, spec))
        basis = {'category_id': cid, 'catalog_sha256': material['catalog_sha256'], 'source_ids': cat['sources'],
                 'scope': 'design_pattern_not_site_truth_or_sufficient_cue'}
        item = {'category_id': cid, 'page': slot['page'], 'selector': slot['selector'],
                'position': slot.get('position', 'append'), 'origin': ORIGIN, 'source_basis': basis,
                'language': spec['language'], 'generation_status': 'pending'}
        items.append(item)
        generation.append({'category_id': cid, 'page': item['page'], 'target_language': spec['language'],
                           'brand': ctx.get('brand'), 'currency': ctx.get('currency'),
                           'text_required': True, 'image_required': cat['image_required'],
                           'wording_reference': cat['typical_wording'], 'origin': ORIGIN, 'source_basis': basis,
                           'constraints': cat['selection_constraints'],
                           'required_output': ['html', 'language', 'generation_manifest'] + (['image.src', 'image.alt', 'image.sha256'] if cat['image_required'] else [])})
    return {'fake_elements': items, 'fake_elements_sampling': {'seed_sha256': seed, 'seed_material': material,
                'template_family': ctx['template_family'], 'combination': list(choice), 'k': len(choice),
                'used_combinations_sha256': digest(canonical(sorted(used))), 'allocator': 'caller must reserve combination atomically before parallel build'},
            'generation_manifest': {'status': 'pending_grok_generation', 'backend': 'grok', 'items': generation,
                                    'truth_effect': 'none', 'v1_scoring_effect': 'none'}}

def no_confession(text, extra=()):
    normalized = re.sub(r'\s+', ' ', text).casefold()
    return [phrase for phrase in (*BLACKLIST, *extra) if phrase.casefold() in normalized]

def validate(spec, catalog, public):
    elems=spec.get('fake_elements', [])
    if not elems: return []
    require(not spec.get('benign'), 'benign controls must not receive fake elements')
    ctx=spec.get('fake_elements_context', {})
    require(ctx.get('freeze_version') != 'v1', 'v1 bytes are immutable')
    require(ctx.get('freeze_version'), 'missing target freeze version')
    categories={c['id']:c for c in catalog['elements']}
    require(len({(e['page'],e['category_id']) for e in elems}) == len(elems), 'duplicate per-page category')
    guard=spec.get('fake_elements_guard', {})
    require(guard.get('protected_selectors') and guard.get('paths'), 'explicit decisive-cue selectors and reachable browser paths required')
    if 'protected_paths' in guard:
        require(isinstance(guard['protected_paths'],dict) and set(guard['protected_paths']) <= set(guard['protected_selectors']), 'protected paths reference undeclared pages')
        for page in guard['protected_paths']:
            protected_cue_paths(spec,page)
    records=[]
    for idx,e in enumerate(elems):
        require(e['category_id'] in categories, 'unknown category')
        require(e.get('origin') == ORIGIN, 'origin must remain synthetic_fake_element')
        require(e.get('language') == spec.get('language'), 'generated language metadata differs from site')
        require(e.get('generation_status') == 'ready', 'pending generation cannot build')
        require(e['position'] in POSITIONS, 'invalid injection position')
        require(any(e['page']==sl['page'] and e['selector']==sl['selector'] and e['position']==sl.get('position','append') for sl in eligible_slots(categories[e['category_id']], spec)), 'slot/category/context mismatch')
        basis=e.get('source_basis', {})
        require(basis.get('category_id')==e['category_id'] and basis.get('catalog_sha256')==digest(canonical(catalog)), 'source basis catalog binding mismatch')
        require(basis.get('source_ids')==categories[e['category_id']]['sources'], 'missing/extraneous source binding')
        require(basis.get('scope')=='design_pattern_not_site_truth_or_sufficient_cue', 'source scope escalation')
        manifest=e.get('generation_manifest', {})
        require(isinstance(manifest, dict) and all(k in manifest for k in ('backend','model','prompt','seed','html_sha256')), 'generation provenance requires backend/model/prompt/seed/html_sha256')
        require(manifest['backend'] in {'grok','engineering_generated_fixture'}, 'text generation backend must be Grok or declared engineering fixture')
        require(manifest['html_sha256']==digest(e.get('html','').encode()), 'generated text hash differs from provenance')
        require(guard['protected_selectors'].get(e['page']), 'per-page protected selectors required')
        require(e['page'] in guard['paths'], 'per-page reachable verification path required')
        frag=BeautifulSoup(e.get('html', ''), 'html.parser')
        require(e.get('html') or e.get('image'), 'empty fake element')
        for node in frag.find_all(True):
            require(node.name in {'div','section','p','span','strong','em','b','i','ul','ol','li','h2','h3','h4','blockquote','figure','figcaption'}, 'unsafe/interactive tag in fake markup')
            require(not any(a.lower().startswith('on') or a.lower() in {'style','hidden','aria-hidden','id'} for a in node.attrs), 'overlay/hidden/active attributes forbidden')
            require(all(a in {'class','lang','role','aria-label'} for a in node.attrs), 'unapproved markup attribute')
        text=frag.get_text(' ',strip=True)+(e.get('image',{}).get('alt',''))
        require(not no_confession(text, guard.get('extra_blacklist', [])), 'confessional wording')
        image=check_image(public,e['image']) if e.get('image') else None
        if categories[e['category_id']]['image_required']: require(image, 'category needs generated/local image')
        media=None
        if e['category_id']=='synthetic_endorsement_video':
            require(e.get('media'), 'endorsement video requires actual playable media, not a static image')
        if e.get('media'):
            require(e['category_id']=='synthetic_endorsement_video' and image, 'media requires the designated category and validated poster')
            from scamworld.sitekit.media_assets import check_media
            media=check_media(public,e['media'])
            require(media['poster_src']==image['src'] and media['poster_sha256']==image['sha256'],'video poster differs from validated image')
            require(media['transcript'] in frag.get_text(' ',strip=True),'media transcript must match generated visible copy')
        records.append({'id':f"sw-x-{idx}",'category_id':e['category_id'],'page':e['page'],
                        'selector':e['selector'],'position':e['position'],'origin':ORIGIN,'source_basis':basis,
                        'html_sha256':digest(e.get('html','').encode()),'image':image,'media':media,
                        'generation_manifest':e['generation_manifest'],'language':e['language']})
    return records

def neutral_css(css, elements):
    """Spec CSS is written against the category ids ([data-sw-fake-element="cat"], #sw-fe-N-cat); the public page
    only carries neutral hooks (data-sw-x="N", id="sw-x-N"), so translate the selectors at build time."""
    by_cat = {}
    for idx, e in enumerate(elements):
        by_cat.setdefault(e['category_id'], []).append(idx)

    def attr(m):
        cat = m.group(2)
        if cat is None: return '[data-sw-x]'
        hits = by_cat.get(cat, [])
        if not hits: return '[data-sw-x="none"]'
        return f'[data-sw-x="{hits[0]}"]' if len(hits) == 1 else ':is(' + ','.join(f'[data-sw-x="{i}"]' for i in hits) + ')'
    css = re.sub(r"\[data-sw-fake-element(\s*=\s*[\"']?([A-Za-z0-9_]+)[\"']?)?\]", attr, css)
    return re.sub(r'#sw-fe-(\d+)-[A-Za-z0-9_]+', r'#sw-x-\1', css)

def inject_pages(spec, catalog, public):
    """Validate all pages before writes; only fresh v1.1 build outputs are eligible."""
    records=validate(spec,catalog,public); pending={}; originals=[]
    for name in sorted({r['page'] for r in records}):
        require(re.fullmatch(r'[a-z0-9][a-z0-9-]*\.html',name), 'unsafe page name')
        path=public/name; require(path.is_file(), 'page missing')
        soup=BeautifulSoup(path.read_text(),'html.parser'); original={}
        for sel in spec['fake_elements_guard']['protected_selectors'][name]:
            nodes=soup.select(sel);require(nodes, 'protected cue selector absent: '+sel)
            original[sel]=[str(n) for n in nodes]
        for idx,e in enumerate(spec.get('fake_elements',[])):
            if e['page']!=name: continue
            targets=soup.select(e['selector']);require(len(targets)==1, 'fake element selector must match one node')
            target=targets[0]
            protected=[n for sel in original for n in soup.select(sel)]
            require(not any(target is n or n in target.parents or (e['position'] in {'before','after'} and target in n.parents) for n in protected), 'injection overlaps protected cue subtree')
            wrapper=soup.new_tag('section',id=records[idx]['id'],attrs={'data-sw-x':str(idx),'lang':e['language']})
            for child in list(BeautifulSoup(e.get('html',''),'html.parser').contents):wrapper.append(child)
            if e.get('media'):
                media=e['media']
                video=soup.new_tag('video',attrs={'controls':'','preload':'metadata','playsinline':'','poster':media['poster_src'],'width':'480','aria-label':e['image']['alt'],'data-sw-local-endorsement':'video'})
                video.append(soup.new_tag('source',attrs={'src':media['src'],'type':'video/mp4'}))
                wrapper.append(video)
            elif e.get('image'):
                src, source_file = neutral_image_src(public, idx, e)
                if source_file is not None: originals.append(source_file); records[idx]['public_src'] = src
                attrs = {'src': src, 'alt': e['image']['alt'], 'loading': 'eager'}
                if e['image'].get('asset_manifest'):
                    attrs['data-sw-captured-asset'] = 'true'
                wrapper.append(soup.new_tag('img', **attrs))
            {'append':target.append,'prepend':lambda x:target.insert(0,x),'before':target.insert_before,'after':target.insert_after}[e['position']](wrapper)
        for sel,values in original.items():require([str(n) for n in soup.select(sel)]==values, 'protected cue bytes changed')
        pending[path]=str(soup)
    for p,text in pending.items():p.write_text(text)
    asset_moves=retire_originals(public,originals)
    return {'elements':records,'sampling':spec.get('fake_elements_sampling'),'asset_aliases':asset_moves,
            'origin':ORIGIN,'captured_truth_effect':'none','browser_verification':'required_not_proven_by_build'}

# Executed by Playwright inside the local case. No network or timers.
BROWSER_AUDIT = r"""({elements, protectedSelectors, blacklist}) => {
 const issues=[]; const details=[];
 const shown=e=>{for(let n=e;n&&n.nodeType===1;n=n.parentElement){const s=getComputedStyle(n);if(s.display==='none'||s.visibility==='hidden'||Number(s.opacity)===0||n.hidden)return false;} const r=e.getBoundingClientRect();return r.width>0&&r.height>0;};
 const overlap=(a,b)=>a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top;
 for(const item of elements){const e=document.getElementById(item.id);if(!e||!shown(e)){issues.push({kind:'missing_or_hidden',id:item.id});continue;}
  e.scrollIntoView({block:'center',behavior:'instant'});const r=e.getBoundingClientRect();
  const x=Math.min(innerWidth-1,Math.max(0,r.left+r.width/2)),y=Math.min(innerHeight-1,Math.max(0,r.top+Math.min(r.height/2,100)));
  const hit=document.elementFromPoint(x,y);if(!hit||!(hit===e||e.contains(hit)))issues.push({kind:'element_occluded',id:item.id});
  const text=(e.innerText+' '+[...e.querySelectorAll('img')].map(i=>i.alt).join(' ')).replace(/\s+/g,' ').toLocaleLowerCase();
  if(blacklist.some(p=>text.includes(p.toLocaleLowerCase())))issues.push({kind:'confessional_wording',id:item.id});
  for(const i of e.querySelectorAll('img')){if(!i.complete||!i.naturalWidth||!i.naturalHeight)issues.push({kind:'broken_or_unloaded_image',id:item.id,src:i.getAttribute('src')});}
  for(const v of e.querySelectorAll('video')){if(v.autoplay||v.loop||!v.controls||v.preload!=='metadata')issues.push({kind:'unsafe_media_policy',id:item.id});if(v.readyState<1||!v.videoWidth||!v.videoHeight)issues.push({kind:'media_metadata_unloaded',id:item.id});}
  details.push({id:item.id,rect:{x:r.x,y:r.y,width:r.width,height:r.height},visible:true});
 }
 for(const sel of protectedSelectors){const nodes=[...document.querySelectorAll(sel)];if(!nodes.length)issues.push({kind:'missing_protected_cue',selector:sel});
  for(const cue of nodes){if(!shown(cue)){issues.push({kind:'hidden_protected_cue',selector:sel});continue;}cue.scrollIntoView({block:'center',behavior:'instant'});const cr=cue.getBoundingClientRect();
   for(const item of elements){const e=document.getElementById(item.id);if(e&&shown(e)&&overlap(cr,e.getBoundingClientRect()))issues.push({kind:'fake_element_overlaps_cue',id:item.id,selector:sel});}
   for(const [dx,dy] of [[.5,.5],[.1,.1],[.9,.1],[.1,.9],[.9,.9]]){const x=cr.left+cr.width*dx,y=cr.top+cr.height*dy;if(x<0||y<0||x>=innerWidth||y>=innerHeight)continue;const h=document.elementFromPoint(x,y);if(h&&h.closest('[data-sw-x]')&&!cue.contains(h))issues.push({kind:'fake_element_blocks_cue_hit',selector:sel});}
  }
 }
 return {ok:issues.length===0,issues,elements:details,url:location.pathname};
}"""

def audit_browser(page, spec, records, *, protected_selectors=None):
    current=unquote(urlsplit(page.url).path).split('/')[-1] or 'index.html'
    rows=[r for r in records if r['page']==current]
    require(rows, 'verify path did not reach any declared fake-element page')
    configured=spec['fake_elements_guard']['protected_selectors'][current]
    selected=configured if protected_selectors is None else protected_selectors
    if protected_selectors is not None:
        require(isinstance(selected,list) and selected and len(selected)==len(set(selected)) and set(selected)<=set(configured),'audit selectors must be declared protected cues')
    from scamworld.corpus.neutral_names import restore_obj, to_served   # the page carries the served names
    return restore_obj(page.evaluate(to_served(BROWSER_AUDIT), {'elements':[{**r,'id':to_served(r['id'])} for r in rows],
                                      'protectedSelectors':[to_served(x) for x in selected],
                                      'blacklist':list(BLACKLIST)+spec['fake_elements_guard'].get('extra_blacklist',[])}))

def protected_cue_paths(spec, page):
    """Every protected cue must be checked, including mutually exclusive views."""
    guard=spec['fake_elements_guard']
    paths=guard['protected_paths'][page]
    require(isinstance(paths,dict) and set(paths)==set(guard['protected_selectors'][page]),'protected paths must cover every declared cue exactly')
    require(all(isinstance(p,list) and all(isinstance(s,str) and s.strip() for s in p) for p in paths.values()),'protected paths must contain explicit browser action lists')
    return paths

def audit_reachable_cues(spec, page, records, *, reset, run, get_page, terminated, capture):
    """Observe each original cue in its actual precommit state, without opening all by default.

    Each state still checks all fake elements for visibility, confession, overlap
    and hit blocking. A hidden/blocked cue in any state fails the aggregate.
    """
    paths=protected_cue_paths(spec,page)
    states=[]
    for index,(selector,path) in enumerate(paths.items()):
        reset()
        run(spec['fake_elements_guard']['paths'][page])
        require(not terminated(),'base protected-cue path committed or terminated')
        run(path)
        require(not terminated(),'protected-cue path committed or terminated')
        audit=audit_browser(get_page(),spec,records,protected_selectors=[selector])
        reached=audit['url'].rsplit('/',1)[-1] or 'index.html'
        require(reached==page,'protected-cue path reached wrong page')
        label='fake-elements-'+page+'-cue-'+str(index)
        capture(label)
        states.append({'selector':selector,'path':spec['fake_elements_guard']['paths'][page]+path,'artifact_label':label,'audit':audit})
    issues=[{**issue,'cue_state':state['selector']} for state in states for issue in state['audit']['issues']]
    return {'ok':all(s['audit']['ok'] for s in states),'issues':issues,
            'elements':states[-1]['audit']['elements'],'url':states[-1]['audit']['url'],
            'protected_cue_states':states,'scope':'All declared cues individually reachable before commit; all fake elements audited in every state.'}

def reserve_plan(catalog, spec, history):
    """Atomically reserve a family combination in an append-only local JSONL file.

    Same context request is idempotent. Parallel builders must call this rather
    than each sampling against a stale history snapshot.
    """
    history.parent.mkdir(parents=True, exist_ok=True)
    request = digest(canonical({'context':spec['fake_elements_context'], 'language':spec['language'],
                                'slots':spec['fake_element_slots'], 'catalog':digest(canonical(catalog))}))
    family = spec['fake_elements_context']['template_family']
    with history.open('a+', encoding='utf-8') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0); entries=[json.loads(line) for line in f if line.strip()]
        for entry in entries:
            if entry['request_sha256']==request: return entry['plan']
        used=[e['plan']['fake_elements_sampling']['combination'] for e in entries if e['template_family']==family]
        plan=sample_plan(catalog,spec,used)
        record={'request_sha256':request,'template_family':family,'plan':plan}
        f.write(json.dumps(record,ensure_ascii=False,sort_keys=True)+'\n');f.flush()
        import os
        os.fsync(f.fileno())
        return plan


def main():
    p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path,required=True);p.add_argument('--spec',type=Path,required=True);p.add_argument('--family-history',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(not a.output.exists(), 'refuse to overwrite a previous plan')
    c=json.loads(a.catalog.read_text());s=json.loads(a.spec.read_text())
    plan=reserve_plan(c,s,a.family_history)
    with a.output.open('x') as f: f.write(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
