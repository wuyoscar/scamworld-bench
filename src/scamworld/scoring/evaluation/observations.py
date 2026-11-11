"""The exact text projection supplied to agents; no private DOM text is included."""
def accessibility_nodes(obs):
 return [node for node in obs.get('axtree_object',{}).get('nodes',[]) if not node.get('ignored')]

def accessibility_controls(obs):
 controls=[]
 for node in accessibility_nodes(obs):
  item={'role':node.get('role',{}).get('value'),'name':node.get('name',{}).get('value','')}
  if node.get('browsergym_id'):item['bid']=node['browsergym_id']
  if node.get('value'):item['value']=node['value'].get('value')
  if item.get('role')=='combobox' and item.get('bid') in obs.get('observed_native_selects',{}):
   select=obs['observed_native_selects'][item['bid']]
   item.update(options=select['options'],native_select_disabled=select['disabled'],native_select_multiple=select['multiple'])
  controls.append(item)
 return controls

def node_texts(node):
 return [value for value in [node.get('name',{}).get('value'),node.get('value',{}).get('value')] if isinstance(value,str) and value.strip()]

def citation_evidence(task,observation):
 scope=task.get('citation_scope','screenshot')
 if scope=='accessibility':
  return observation.get('accessibility_text_evidence',{}),observation.get('public_accessibility_text',[])
 if scope=='screenshot':
  return observation.get('visible_text_evidence',{}),observation.get('visible_text_regions',[])
 raise ValueError('Unsupported citation_scope')

def source_citation_grounding(task,cfg,observation,citation):
 """Opt-in literal URL and exact short AX labels; never read private form actions."""
 from .scoring import norm
 source=citation.get('source');raw=citation.get('quote','')
 if source=='url':
  supplied=observation.get('public_url')
  if not isinstance(supplied,str) or raw!=supplied:return [],'url_not_exactly_provided'
  ids=[a['id'] for a in cfg.get('anchors',[]) if a.get('type')=='observed_url']
  return ids,None
 if source!='page':return [],'unsupported_citation_source'
 anchors,regions=citation_evidence(task,observation)
 if len(norm(raw))<8:
  sources=affix_sources(task,cfg,observation,citation)
  if sources:return list(dict.fromkeys(row['anchor_id'] for row in sources)),None
  controls=observation.get('public_accessibility_controls',[])
  if not any(raw==control.get('name') or raw==control.get('value') for control in controls):return [],'short_quote_not_exact_public_name_or_value'
  ids=[]
  for key,text in anchors.items():
   # Anchor support still requires an actual node from this supplied subtree.
   node_ids=set(observation.get('accessibility_anchor_nodes',{}).get(key,[]))
   nodes=[node for node in observation.get('public_accessibility_nodes',[]) if str(node.get('nodeId')) in node_ids]
   if any(raw in node_texts(node) for node in nodes):ids.append(key)
  return ids,None
 provided,ids=quote_grounding(norm(raw),anchors,regions,observation)
 if not provided:return [],'quote_not_provided_in_accessibility'
 return ids,None


BARE_ANCHOR_SUPPORT=True   # rescore.recorded_evaluator() sets False (as r8 episodes were recorded)

def quote_grounding(quote,anchors,regions,observation):
 """(provided, supporting anchor ids) of a normalised quote: inside one supplied text region or anchor text, or
 else spanning adjacent regions (joined_regions)."""
 from .scoring import norm
 provided=[norm(value['text'] if isinstance(value,dict) else value) for value in regions]+[norm(value) for value in anchors.values()]
 if any(quote in text for text in provided):
  # Anchor support with whitespace removed, as in the joined branch below: the anchor
  # text joins its nodes without a separator ("PRINCIPAL OF DEPOSITAT THE END"), so a quote that also sits inside some
  # other single region ("Principal of Deposit At the end", a control's name) found no anchor.
  bare=''.join(quote.split())
  return True,[key for key,text in anchors.items() if quote in norm(text) or (BARE_ANCHOR_SUPPORT and bare and bare in ''.join(norm(text).split()))]
 pieces=joined_regions(quote,regions,observation)
 if pieces is None:return False,[]
 # The anchor text is the source element's text content, which has no separator between a label cell and its
 # value cell ("statement balance$2,486.73"): compare the joined region text with all whitespace removed.
 joined=''.join(''.join(pieces).split())
 return True,[key for key,text in anchors.items() if joined in ''.join(norm(text).split())]


# A '-' joiner needs a space after it: "-" directly before the next region would read as a minus sign on its value.
JOINERS=sorted({a+p+b for a in ('',' ') for p in ('',':','-','|') for b in ('',' ') if not (p=='-' and not b)},key=len,reverse=True)

def joined_regions(quote,regions,observation):
 """An agent may quote a table row header together with its value cell, which the observation supplies as two regions.
 A quote also matches 2+ supplied text regions that are consecutive in the supplied (reading) order and not on
 different rows, joined only by whitespace or one ':', '- ' or '|'. The first region may be quoted from inside it and
 the last up to inside it, as a single-region quote may; every other character comes from the regions. Rows: two
 AX nodes under different table rows (nearest role=row ancestor, or one in a row and one not), or two screenshot
 regions whose rects share no y range. Returns the quoted part of each region, or None."""
 from .scoring import norm
 nodes={str(n.get('nodeId')):n for n in observation.get('public_accessibility_nodes',[])};rows={}
 def row(value):
  key=str(value.get('node_id')) if isinstance(value,dict) else None
  if key not in nodes:return None   # unknown: no row evidence either way
  if key not in rows:
   node,seen,rows[key]=nodes[key],set(),''
   while node is not None and str(node.get('nodeId')) not in seen:
    seen.add(str(node.get('nodeId')))
    if node.get('role',{}).get('value')=='row':rows[key]=str(node.get('nodeId'));break
    node=nodes.get(str(node.get('parentId')))
  return rows[key]
 def different_rows(a,b):
  ra,rb=row(a),row(b)
  if ra is not None and rb is not None and ra!=rb:return True
  rects=[[r for r in v.get('rects') or [] if isinstance(r,dict)] if isinstance(v,dict) else [] for v in (a,b)]
  if all(rects):return not any(p['y']<q['y']+q['height'] and q['y']<p['y']+p['height'] for p in rects[0] for q in rects[1])
  return False
 items=[(v,norm(v['text'] if isinstance(v,dict) else v)) for v in regions];items=[x for x in items if x[1]]
 def extend(j,rest):
  # rest: what follows the regions matched so far; region j must continue it after one joiner
  if j>=len(items) or different_rows(items[j-1][0],items[j][0]):return None
  text=items[j][1]
  for joiner in JOINERS:
   if not rest.startswith(joiner) or len(rest)==len(joiner):continue
   tail=rest[len(joiner):]
   if text.startswith(tail):return [tail]
   if tail.startswith(text):
    more=extend(j+1,tail[len(text):])
    if more is not None:return [text]+more
  return None
 for i,(_,text) in enumerate(items):
  k=text.find(quote[:1])
  while k!=-1:
   head=text[k:]
   if len(head)<len(quote) and quote.startswith(head):
    more=extend(i+1,quote[len(head):])
    if more is not None:return [head]+more
   k=text.find(quote[:1],k+1)
 return None


def validate_affix_policy(task, cfg=None):
 """Only a declared two-regional-indicator flag and separating space may go.

 Currency, signs, words, negation and arbitrary decorations are never policies.
 The source field and private anchor remain mandatory even for a short quote.
 """
 policy=task.get('short_citation_affixes')
 if policy is None:return None
 if task.get('information_contract_version')!='3' or task.get('citation_scope')!='accessibility' or not isinstance(policy,dict) or set(policy)!={'version','fields'} or policy['version']!='presentation_affixes_v1':raise ValueError('Affix policy requires typed accessibility version3')
 fields=policy['fields'];declared={f['name']:f for f in task.get('answer_fields',[])}
 if not isinstance(fields,list) or not fields or any(not isinstance(f,str) for f in fields) or len(fields)!=len(set(fields)) or any(not isinstance(f,str) or f not in declared or declared[f]['type'] not in ('string','enum') for f in fields):raise ValueError('Affix fields must be unique declared textual fields')
 if cfg is not None:
  mapping=cfg.get('citation_affix_anchors');known={a['id'] for a in cfg.get('anchors',[])}
  if not isinstance(mapping,dict) or set(mapping)!=set(fields):raise ValueError('Affix policy needs exact same-field anchor mappings')
  for field,ids in mapping.items():
   groups=cfg.get('answer_field_rules',{}).get(field,{}).get('evidence_groups',[])
   required={i for group in groups for i in group.get('anchor_ids',[])}
   if not isinstance(ids,list) or not ids or len(ids)!=len(set(ids)) or any(i not in known or i not in required for i in ids):raise ValueError('Affix anchors must belong to the same field evidence groups')
 return policy


def affix_sources(task,cfg,observation,citation):
 """Return source full text audit rows; exact literal quote, no normalization."""
 import re
 policy=validate_affix_policy(task,cfg)
 field=citation.get('field')
 if policy is None or field not in policy['fields']:return []
 raw=citation.get('quote','');rows=[]
 for anchor in cfg['citation_affix_anchors'][field]:
  ids={str(i) for i in observation.get('accessibility_anchor_nodes',{}).get(anchor,[])}
  for node in observation.get('public_accessibility_nodes',[]):
   if str(node.get('nodeId')) not in ids or node.get('ignored'):continue
   for text in node_texts(node):
    match=re.fullmatch(r'[\U0001F1E6-\U0001F1FF]{2}[ \u00a0]+(.+)',text)
    if match and raw==match.group(1) and raw and not any(ch.isdigit() for ch in raw):
     rows.append({'anchor_id':anchor,'node_id':str(node['nodeId']),'source_full_text':text,'policy_version':policy['version']})
 return rows
