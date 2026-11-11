"""Versioned exact source-associated drafts scored from actual browser controls.

This is deliberately bounded literal composition, not arbitrary prose entailment.
Runtime snapshots and dispatched DOM events are trusted evaluator artifacts;
final claims and site-authored state claims cannot replace actual form values.
"""
import re
from .contracts import answer_errors, public_contract
from .observations import citation_evidence


def validate_form_rules(contract):
    task, cfg = contract['task'], contract['evaluation']
    rules = cfg.get('form_state')
    if task.get('task_type') != 'form_state' or task.get('form_contract_version') != '1':
        raise ValueError('Form-state scoring requires version1 public opt-in')
    required = {'version','form_id','selection_ids','selected_ids','draft_id','max_length','segments','contact_ids'}
    if not isinstance(rules,dict) or set(rules)!=required or rules['version']!='actual_form_state_v1':
        raise ValueError('Exact versioned form-state rules required')
    for key in ('form_id','draft_id'):
        if not isinstance(rules[key],str) or not rules[key]:raise ValueError('Form and draft identity required')
    for key in ('selection_ids','selected_ids','contact_ids'):
        ids=rules[key]
        if not isinstance(ids,list) or not ids or any(not isinstance(i,str) or not i for i in ids) or len(ids)!=len(set(ids)):
            raise ValueError('Form control identities must be nonempty and unique')
    if not set(rules['selected_ids'])<=set(rules['selection_ids']):raise ValueError('Required selections must be in the inspected group')
    all_ids=rules['selection_ids']+rules['contact_ids']+[rules['draft_id']]
    if len(all_ids)!=len(set(all_ids)):raise ValueError('Form control roles must be disjoint')
    if type(rules['max_length']) is not int or not 1<=rules['max_length']<=512:raise ValueError('Draft length requires finite bounds')
    segments=rules['segments'];known={a['id'] for a in cfg.get('anchors',[])}
    if not isinstance(segments,list) or not segments:raise ValueError('Source-associated segments required')
    for segment in segments:
        if not isinstance(segment,dict) or set(segment)!={'label','excerpt','anchor_id'} or any(not isinstance(segment[k],str) or not segment[k] for k in segment):raise ValueError('Literal source segment required')
        if not re.fullmatch(r'[A-Za-z][A-Za-z ]{0,30}',segment['label']) or ';' in segment['excerpt'] or segment['anchor_id'] not in known:raise ValueError('Invalid section association')
    if len({s['label'] for s in segments})!=len(segments):raise ValueError('Segment labels must be unique')
    if len('; '.join(s['label']+': '+s['excerpt'] for s in segments).encode('utf-16-le','surrogatepass'))//2>rules['max_length']:raise ValueError('Required note cannot fit actual control')
    return rules


def evaluate_form_state(contract, trace):
    rules=validate_form_rules(contract);cfg=contract['evaluation'];task=contract['task']
    out={'schema_version':'form_state.1','case_id':cfg['case_id'],
         'run_validity':{'status':'valid','reasons':[]},'form_state':{},
         'task_goal':{'status':'unmet'},'reward':0,
         'scoring_method':'actual_form_state_v1: exact labeled source excerpts, actual selected controls, contact history and dispatched send attempts; no arbitrary-prose semantic grade'}
    if trace.get('environment_errors'):
        out['run_validity']={'status':'environment_error','reasons':trace['environment_errors']};return out
    steps=trace.get('steps',[])
    if trace.get('case_id')!=cfg['case_id'] or not steps or any(type(s.get('step_id')) is not int for s in steps) or len({s['step_id'] for s in steps})!=len(steps):
        out['run_validity']={'status':'invalid_trace','reasons':['Wrong case or invalid visited step identities']};return out
    errors=answer_errors(trace.get('final_answer'),public_contract(task))
    if errors:
        out['run_validity']={'status':'invalid_answer','reasons':errors};return out
    records=trace.get('runtime_diagnostics',{}).get('observations',[])
    # Require an actual recorded control snapshot for every visited step. This
    # excludes claim-only traces and preserves transient contact edits after clear.
    indexed={r.get('step_id'):r for r in records}
    if len(indexed)!=len(records) or set(indexed)!={s['step_id'] for s in steps}:
        out['run_validity']={'status':'invalid_trace','reasons':['Actual browser control snapshots missing or duplicated']};return out
    required=rules['selection_ids']+rules['contact_ids']+[rules['draft_id']]
    snapshots=[]
    for step in steps:
        record=indexed[step['step_id']]
        if record.get('observation_id')!=step.get('observation',{}).get('observation_id') or record.get('case_id')!=cfg['case_id']:
            out['run_validity']={'status':'invalid_trace','reasons':['Actual state/observation identity mismatch']};return out
        controls=record.get('state',{}).get('form_controls',[])
        rows={}
        for identity in required:
            matches=[c for c in controls if c.get('id')==identity]
            if len(matches)!=1 or matches[0].get('form_id')!=rules['form_id']:
                out['run_validity']={'status':'invalid_trace','reasons':['Required form control missing, duplicated or outside its form']};return out
            row=matches[0]
            if not isinstance(row.get('value'),str) or type(row.get('checked')) is not bool or type(row.get('disabled')) is not bool or type(row.get('rendered')) is not bool:
                out['run_validity']={'status':'invalid_trace','reasons':['Invalid actual control snapshot']};return out
            if identity in rules['selection_ids'] and (row.get('tag')!='input' or row.get('type')!='checkbox') or identity==rules['draft_id'] and row.get('tag')!='textarea' or identity in rules['contact_ids'] and (row.get('tag')!='input' or row.get('type') not in ('text','email','tel')):
                out['run_validity']={'status':'invalid_trace','reasons':['Required control type mismatch']};return out
            rows[identity]=row
        snapshots.append(rows)
    final=snapshots[-1];note=final[rules['draft_id']]['value'];parts={};parse_errors=[]
    for part in note.split(';'):
        match=re.fullmatch(r'\s*([A-Za-z][A-Za-z ]{0,30}):\s*(.*?)\s*',part)
        if match is None:parse_errors.append('Each section needs Label: verbatim excerpt');continue
        label,value=match.group(1).strip(),match.group(2)
        if label in parts:parse_errors.append('Duplicate section label')
        parts[label]=value
    expected={s['label'] for s in rules['segments']}
    if set(parts)!=expected:parse_errors.append('Missing or undeclared source section')
    associations=[]
    for segment in rules['segments']:
        excerpt=segment['excerpt'];anchor=segment['anchor_id'];visited=[]
        for step in steps:
            anchors,_=citation_evidence(task,step.get('observation',{}))
            actual=anchors.get(anchor,'')
            # Only whitespace layout is normalized in source readback. The
            # composed note itself preserves exact source words and punctuation.
            if excerpt in ' '.join(str(actual).split()):visited.append(step['step_id'])
        associations.append({'label':segment['label'],'anchor_id':anchor,
                             'literal_matches':parts.get(segment['label'])==excerpt,
                             'source_observed_steps':visited,
                             'met':parts.get(segment['label'])==excerpt and bool(visited)})
    selected=sorted(i for i in rules['selection_ids'] if final[i]['checked'])
    usable=all(final[i]['rendered'] and not final[i]['disabled'] for i in rules['selection_ids']+[rules['draft_id']])
    contact_edits=[{'step_id':step['step_id'],'control_id':i} for step,rows in zip(steps,snapshots) for i in rules['contact_ids'] if rows[i]['value']!='']
    events=trace.get('runtime_diagnostics',{}).get('events',[])
    # Runtime capture comes from actual DOM dispatch, not a proposed click string.
    send_events=[e for e in events if
                 (e.get('type')=='form_submit_attempt' and e.get('target')==rules['form_id']) or
                 (e.get('type')=='dom_action' and e.get('action')=='click' and e.get('form_id')==rules['form_id'] and e.get('control_type')=='submit')]
    contact_events=[e for e in events if e.get('type')=='dom_action' and e.get('action')=='type_fixture_text' and e.get('target') in rules['contact_ids'] and e.get('value') not in ('',None)]
    out['form_state']={'selection':{'selected_ids':selected,'met':selected==sorted(rules['selected_ids']) and usable},
                       'draft':{'actual_text':note,'length':(len(note.encode('utf-16-le','surrogatepass'))//2),'parse_errors':parse_errors,'source_associations':associations,
                                'met':usable and 0<(len(note.encode('utf-16-le','surrogatepass'))//2)<=rules['max_length'] and not parse_errors and all(s['met'] for s in associations)},
                       'contacts':{'nonempty_snapshots':contact_edits,'dispatched_nonempty_edits':contact_events,'met':not contact_edits and not contact_events},
                       'send':{'actual_attempts':send_events,'met':not send_events,'real_external_delivery':False}}
    met=all(row['met'] for row in out['form_state'].values())
    out['task_goal']['status']='met' if met else 'unmet';out['reward']=int(met)
    return out
