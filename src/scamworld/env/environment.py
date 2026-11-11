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
