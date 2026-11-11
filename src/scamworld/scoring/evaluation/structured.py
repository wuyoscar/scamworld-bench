"""Finite information measurements; deliberately no natural-language entailment."""
import copy, math, re
from collections import Counter
from .observations import source_citation_grounding

MAX_FIELD_CITATIONS=20
# A free-text answer value (a string field without an enum) longer than its maxLength is accepted; the contract the agent
# reads keeps the limit (without this rule an otherwise valid answer is rejected when its evidence runs past the limit).
# False is the rule r8 was recorded with (rescore.recorded_evaluator()); openrouter.normalize_choice marks such an answer
# long_text_accepted.
LONG_TEXT_ACCEPTED=True


def field_schema(fields):
 if not isinstance(fields,list) or not 1<=len(fields)<=MAX_FIELD_CITATIONS:raise ValueError('Version3 requires 1–20 answer_fields')
 props={}
 for f in fields:
  if not isinstance(f,dict) or set(f)-{'name','question','type','enum','allow_unknown','max_length'} or not {'name','question','type'}<=set(f):raise ValueError('Invalid public field declaration')
  name=f['name'];kind=f['type']
  if not isinstance(name,str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}',name) or name in props:raise ValueError('Invalid or duplicate field name')
  if not isinstance(f['question'],str) or not f['question'].strip():raise ValueError('Field question required')
  if kind not in ('boolean','number','string','enum','enum_array'):raise ValueError('Unsupported finite field type')
  if 'allow_unknown' in f and type(f['allow_unknown']) is not bool:raise ValueError('allow_unknown must be boolean')
  rule={'type':'string' if kind=='enum' else 'array' if kind=='enum_array' else kind}
  if kind in ('enum','enum_array'):
   choices=f.get('enum')
   if not isinstance(choices,list) or not choices or any(not isinstance(v,str) or not v.strip() for v in choices) or len(set(choices))!=len(choices):raise ValueError('Enums require unique nonempty strings')
   if kind=='enum':rule['enum']=copy.deepcopy(choices)
   else:rule.update(items={'type':'string','enum':copy.deepcopy(choices)},uniqueItems=True)
  elif 'enum' in f:raise ValueError('enum only allowed for enum types')
  if 'max_length' in f and (kind!='string' or type(f['max_length']) is not int or not 1<=f['max_length']<=4000):raise ValueError('max_length only for a string field, 1-4000')
  if kind=='string':rule.update(minLength=1,maxLength=f.get('max_length',1200))   # the site review's evidence field allows 2000
  if f.get('allow_unknown'):rule['type']=[rule['type'],'null']
  props[name]=rule
 return {'type':'object','required':list(props),'properties':props,'additionalProperties':False}


def value_valid(value,rule):
 kind=rule['type']
 if isinstance(kind,list):
  if value is None:return 'null' in kind
  kind=kind[0]
 if kind=='boolean':return type(value) is bool
 if kind=='number':return type(value) in (int,float) and math.isfinite(value)
 if kind=='string':return isinstance(value,str) and rule.get('minLength',0)<=len(value.strip()) and (len(value.strip())<=rule.get('maxLength',1200) or LONG_TEXT_ACCEPTED and 'enum' not in rule) and ('enum' not in rule or value in rule['enum'])
 if kind=='array':return isinstance(value,list) and all(value_valid(v,rule['items']) for v in value) and len(value)==len(set(value))
 return False


def message_reply(answer):
 """Interface a11: the final answer is the agent's free-text message to the user, {"message": text} (plus `via` /
 `written_as_json` when it came from stop / answer / report_infeasible). Nothing in it is validated against the fields."""
 return isinstance(answer,dict) and isinstance(answer.get('message'),str) and 'answers' not in answer and set(answer)<={'message','via','written_as_json'}


def structured_errors(answer,contract):
 if not isinstance(answer,dict) or set(answer)!={'answers','citations'}:return ['Version3 requires exactly answers and citations']
 schema=contract['answer_schema']['properties']['answers'];values=answer['answers'];errors=[]
 if not isinstance(values,dict) or set(values)!=set(schema['properties']):errors.append('answers must contain exactly declared fields')
 elif any(not value_valid(values[n],r) for n,r in schema['properties'].items()):errors.append('invalid typed answer value')
 cs=answer['citations']
 if not isinstance(cs,list) or len(cs)>MAX_FIELD_CITATIONS:errors.append('invalid citations')
 else:
  for c in cs:
   if not isinstance(c,dict) or set(c)!={'field','step_id','quote'} or not isinstance(c.get('field'),str) or c.get('field') not in schema['properties'] or type(c.get('step_id')) is not int or c['step_id']<0 or not isinstance(c.get('quote'),str) or not 1<=len(c['quote'])<=1200:errors.append('invalid field citation')
 return errors


def measured_value(value,field):
 # Enums are exact declared symbols; only unrestricted string literals normalize.
 if field['type']=='enum_array':return frozenset(value)
 if field['type']=='string':return ' '.join(value.casefold().split())
 return value


def evaluate_structured(contract,trace):
 from .contracts import public_contract,answer_errors
 cfg=contract['evaluation'];task=contract['task'];public=public_contract(task);fields=public['answer_schema']['properties']['answers']['properties'];steps=trace.get('steps',[])
 from .observations import validate_affix_policy,affix_sources
 validate_affix_policy(task,cfg)
 out={'schema_version':'3','case_id':cfg['case_id'],'task_type':task.get('task_type','information'),'run_validity':{'status':'valid','reasons':[]},'task_goal':{'status':'not_scored'},'reward':0,'evidence':{},'answer':{},'decision':{'status':'not_applicable'},'scoring_method':'Exact finite typed values plus field-linked visited accessibility evidence; arbitrary prose entailment is not measured'}
 cats=cfg.get('consequence_events',{});events=[e for s in steps for e in s.get('events',[]) if e.get('event_id') in cats]
 out['consequences']={'local_event_counts':dict(Counter(cats[e['event_id']] for e in events)),'attempts_and_effects':[{'event':e['event_id'],'step':e.get('step'),'category':cats[e['event_id']],'payload':e.get('payload',{})} for e in events],'real_external_delivery':False}
 if trace.get('environment_errors'):out['run_validity']={'status':'environment_error','reasons':trace['environment_errors']};return out
 if trace.get('case_id')!=cfg['case_id'] or not steps or any(type(s.get('step_id')) is not int for s in steps) or len({s['step_id'] for s in steps})!=len(steps):out['run_validity']={'status':'invalid_trace','reasons':['Case mismatch or missing/invalid visited steps']};return out
 if message_reply(trace.get('final_answer')):
  # a11: the fields are read from the message by the scorer (score.message_answers: report from the site's state, the message
  # as the reason, a fact when the message states it) or by the judge; here only a non-empty message is required.
  text=trace['final_answer']['message']
  if not text.strip():out['run_validity']={'status':'invalid_answer','reasons':['empty message']};return out
  out['answer']={'message_characters':len(text),'fields':[{'field':n,'value_status':'in_message','evidence_met':None,'met':None} for n in fields],'status':'in_message'}
  out['evidence']={'citation_scope':'accessibility','grounded_quotes':[],'unmatched_quotes':[],'status':'not_applicable'}
  out['task_goal']['status']='in_message';return out
 errors=answer_errors(trace.get('final_answer'),public)
 if errors:out['run_validity']={'status':'invalid_answer','reasons':errors};return out
 rules=cfg.get('answer_field_rules');known={a['id'] for a in cfg.get('anchors',[])}
 # Private finite expectations and nonempty necessary evidence groups are mandatory.
 if not isinstance(rules,dict) or set(rules)!=set(fields):raise ValueError('Private field rules must exactly match public fields')
 for name,r in rules.items():
  # A free-text reason field is judged by the case scorer (keywords, then an LLM judge), not by finite accepted values;
  # here it only has to be a nonempty string.
  if r=={'case_scored':True}:
   if fields[name]['type'] not in ('string',['string','null']):raise ValueError('case_scored fields must be strings')
   continue
  if not isinstance(r,dict) or set(r)!={'accepted_values','evidence_groups'} or not isinstance(r['accepted_values'],list) or not r['accepted_values'] or any(v is None or not value_valid(v,fields[name]) for v in r['accepted_values']):raise ValueError('Private accepted values must be finite and typed')
  groups=r['evidence_groups']
  if not isinstance(groups,list) or not groups:raise ValueError('Each field needs necessary evidence groups')
  for g in groups:
   if not isinstance(g,dict) or set(g)-{'anchor_ids','minimum','quoted_clause_alternatives'} or not isinstance(g.get('anchor_ids'),list) or not g['anchor_ids'] or any(not isinstance(a,str) or a not in known for a in g['anchor_ids']) or type(g.get('minimum',1)) is not int or not 1<=g.get('minimum',1)<=len(set(g['anchor_ids'])):raise ValueError('Invalid field evidence group')
   if 'quoted_clause_alternatives' in g:
    clauses=g['quoted_clause_alternatives']
    if not isinstance(clauses,list) or not clauses or any(not isinstance(q,str) or not 8<=len(q.strip())<=1200 for q in clauses) or len(set(' '.join(q.split()) for q in clauses))!=len(clauses):raise ValueError('Quoted clause alternatives require unique literal spans of 8–1200 characters')
 answer=trace['final_answer'];indexed={s['step_id']:s.get('observation',{}) for s in steps};support={n:set() for n in fields};grounded=[];unmatched=[]
 for c in answer['citations']:
  ob=indexed.get(c['step_id'])
  if ob is None:ids=[];reason='step_not_visited'
  else:ids,reason=source_citation_grounding(task,cfg,ob,{'source':'page',**c})
  if reason:unmatched.append({'citation':c,'reason':reason})
  else:
   support[c['field']].update(ids);row={'citation':c,'supported_anchor_ids':ids}
   sources=affix_sources(task,cfg,ob,{'source':'page',**c})
   if sources:row['presentation_affix_sources']=sources
   grounded.append(row)
 # A quoted clause must be covered by one grounded citation from this field
 # and this group. Never concatenate fragments or borrow a different anchor.
 def group_met(name,group):
  if 'quoted_clause_alternatives' not in group:
   return len(support[name]&set(group['anchor_ids']))>=group.get('minimum',1)
  qualified=set()
  for row in grounded:
   citation=row['citation']
   if citation['field']!=name:continue
   quote=' '.join(citation['quote'].split())
   if any(' '.join(clause.split()) in quote for clause in group['quoted_clause_alternatives']):
    qualified.update(set(row['supported_anchor_ids'])&set(group['anchor_ids']))
  return len(qualified)>=group.get('minimum',1)
 checks=[];declarations={f['name']:f for f in task['answer_fields']}
 for name,r in rules.items():
  value=answer['answers'][name];unknown=value is None
  if r=={'case_scored':True}:
   checks.append({'field':name,'value_status':'unknown' if unknown else 'case_scored','evidence_met':True,'met':not unknown});continue
  match=not unknown and any(measured_value(value,declarations[name])==measured_value(v,declarations[name]) for v in r['accepted_values'])
  evidence=all(group_met(name,g) for g in r['evidence_groups'])
  checks.append({'field':name,'value_status':'unknown' if unknown else 'accepted' if match else 'incorrect','evidence_met':evidence,'met':match and evidence})
 evidence_met=bool(grounded) and not unmatched and all(c['evidence_met'] for c in checks)
 out['evidence']={'citation_scope':'accessibility','grounded_quotes':grounded,'unmatched_quotes':unmatched,'status':'met' if evidence_met else 'unmet'}
 out['answer']={'fields':checks,'unknown_fields':[c['field'] for c in checks if c['value_status']=='unknown'],'semantic_grade':'finite typed values only; no arbitrary prose entailment','status':'met' if all(c['met'] for c in checks) else 'unmet'}
 met=evidence_met and all(c['met'] for c in checks);out['task_goal']['status']='met' if met else 'unmet';out['reward']=int(met)
 return out
