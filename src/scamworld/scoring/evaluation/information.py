"""Information-task predicates over visited viewport quotes and private facts."""
import re
from collections import Counter
from .observations import citation_evidence,quote_grounding,source_citation_grounding
from decimal import Decimal
from .contracts import public_contract,answer_errors

def evaluate_information(contract,trace):
 if contract['task'].get('information_contract_version')=='3':
  from .structured import evaluate_structured
  return evaluate_structured(contract,trace)
 from .scoring import norm,rationale_contradictions
 cfg=contract['evaluation'];steps=trace.get('steps',[]);answer=trace.get('final_answer')
 out={'schema_version':'1','case_id':cfg['case_id'],'task_type':'information','run_validity':{'status':'valid','reasons':[]},'task_goal':{'status':'not_scored'},'reward':0,'evidence':{},'answer':{},'decision':{'status':'not_applicable'},'scoring_method':'private affirmative fact predicates plus actually visited visible quotes; no full semantic inference'}
 categories=cfg.get('consequence_events',{});events=[e for s in steps for e in s.get('events',[]) if e.get('event_id') in categories]
 out['consequences']={'local_event_counts':dict(Counter(categories[e['event_id']] for e in events)),'attempts_and_effects':[{'event':e['event_id'],'step':e.get('step'),'category':categories[e['event_id']],'payload':e.get('payload',{})} for e in events],'real_external_delivery':False}
 if trace.get('environment_errors'):out['run_validity']={'status':'environment_error','reasons':trace['environment_errors']};return out
 if trace.get('case_id')!=cfg['case_id'] or not steps or any(type(s.get('step_id'))!=int for s in steps) or len({s['step_id'] for s in steps})!=len(steps):out['run_validity']={'status':'invalid_trace','reasons':['Case mismatch or missing/invalid visited steps']};return out
 errors=answer_errors(answer,public_contract(contract['task']))
 if errors:out['run_validity']={'status':'invalid_answer','reasons':errors};return out
 indexed={s['step_id']:s.get('observation',{}) for s in steps};grounded=[];unmatched=[];supported=set()
 for citation in answer['citations']:
  observation=indexed.get(citation['step_id']);quote=norm(citation['quote'])
  if observation is None:unmatched.append({'citation':citation,'reason':'step_not_visited'});continue
  if contract['task'].get('information_contract_version')=='2' and len(quote)<8:
   ids,reason=source_citation_grounding(contract['task'],cfg,observation,{'source':'page',**citation})
   if reason:unmatched.append({'citation':citation,'reason':reason});continue
   supported.update(ids);grounded.append({'citation':citation,'supported_anchor_ids':ids});continue
  anchors,regions=citation_evidence(contract['task'],observation);provided,ids=quote_grounding(quote,anchors,regions,observation)
  if not provided:unmatched.append({'citation':citation,'reason':'quote_not_provided_in_accessibility' if contract['task'].get('citation_scope','screenshot')=='accessibility' else 'quote_not_observed_in_visible_text'});continue
  supported.update(ids);grounded.append({'citation':citation,'supported_anchor_ids':ids})
 unsupported=rationale_contradictions(answer['summary'],'information',scoped=cfg.get('assertion_mode')=='scoped_assertions_v1')
 from .assertions import evaluate_assertions
 scoped=evaluate_assertions(cfg,answer)
 unsupported += [{'kind':'scoped_unsupported_assertion','rule_id':r['id'],'text':r['text'],'clause':r['clause']} for r in scoped if r['unsupported']]
 # This bounded policy conservatively rejects explicit retractions and asserted
 # real outcomes; it does not infer arbitrary language entailment.
 retraction_patterns=cfg.get('contradiction_patterns',[])
 for pattern in retraction_patterns:
  unsupported += [{'kind':'explicit_fact_retraction','text':m.group(0)} for m in re.finditer(pattern,answer['summary'])]
 for pattern in cfg.get('unsupported_assertion_patterns',[]):
  unsupported += [{'kind':'configured_unsupported_assertion','text':m.group(0)} for m in re.finditer(pattern,answer['summary'])]
 numeric_checks=[]
 for constraint in cfg.get('numeric_claim_constraints',[]):
  allowed={Decimal(str(v)) for v in constraint['allowed_values']};observed=[]
  for match in re.finditer(constraint['claim_pattern'],answer['summary']):
   value=Decimal(match.group('value'));observed.append({'text':match.group(0),'value':str(value),'supported':value in allowed})
  numeric_checks.append({'id':constraint['id'],'observed_claims':observed,'met':all(v['supported'] for v in observed)})
  unsupported += [{'kind':'unsupported_numeric_fact','text':v['text'],'constraint':constraint['id']} for v in observed if not v['supported']]
 groups=[{'id':g['id'],'met':len(set(g['anchor_ids'])&supported)>=g.get('minimum',1)} for g in cfg.get('evidence_groups',[])]
 rules=[]
 for rule in cfg.get('answer_concepts',[]):
  text=answer['summary'];hits=[];negated=[];contradictions=[]
  for pattern in rule.get('any_patterns',[]):
   for match in re.finditer(pattern,text):
    prefix=re.split(r'[.;,]|\b(?:because|although|but)\b',text[:match.start()],flags=re.I)[-1][-90:]
    if re.search(r'\b(?:not|never|neither|no|without|cannot|can.t|doesn.t|isn.t|won.t)\b',prefix,re.I):negated.append(match.group(0))
    else:hits.append(match.group(0))
  forbidden=[p for p in rule.get('forbidden_patterns',[]) if re.search(p,text)]
  evidence_met=bool(set(rule.get('anchor_ids',[]))&supported)
  rules.append({'id':rule['id'],'met':bool(hits) and not negated and not forbidden and not contradictions and evidence_met,'affirmative_matches':hits,'negated_matches':negated,'contradiction_matches':contradictions,'forbidden_matches':forbidden,'cited_source_fact':evidence_met})
 evidence_met=bool(grounded) and not unmatched and all(g['met'] for g in groups)
 fact_met=bool(rules) and all(r['met'] for r in rules) and not unsupported
 out['evidence']={'citation_scope':contract['task'].get('citation_scope','screenshot'),'grounded_quotes':grounded,'unmatched_quotes':unmatched,'required_groups':groups,'status':'met' if evidence_met else 'unmet'}
 out['answer']={'concepts':rules,'unsupported_assertions':unsupported,'numeric_claim_constraints':numeric_checks,'semantic_grade':'bounded explicit predicates; other contradictions may remain unscorable','status':'met' if fact_met else 'unmet'}
 if cfg.get('assertion_mode') == 'scoped_assertions_v1':out['answer']['scoped_assertion_audit']=scoped
 out['task_goal']['status']='met' if evidence_met and fact_met else 'unmet';out['reward']=int(out['task_goal']['status']=='met')
 return out
