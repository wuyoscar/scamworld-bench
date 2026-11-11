"""Explicit operator-origin comparisons; hosting technology is not fraud proof."""
from urllib.parse import urlsplit

def parsed_origin(url):
 parsed=urlsplit(url)
 if parsed.scheme not in ['http','https'] or not parsed.hostname:raise ValueError('Origin reference requires an http(s) hostname')
 port=parsed.port or (443 if parsed.scheme=='https' else 80)
 return parsed.scheme,parsed.hostname.rstrip('.').encode('idna').decode('ascii').casefold(),port

def evaluate_origin_rules(cfg,grounded,indexed):
 rows=[]
 for rule in cfg.get('origin_rules',[]):
  relation=rule.get('relation')
  if relation not in ['observe_only','outside_reference_origins']:raise ValueError('Unsupported origin relation')
  if relation=='outside_reference_origins' and not rule.get('reference'):raise ValueError('Comparative origin rule needs an explicit operator source reference')
  expected={parsed_origin(url) for url in rule.get('expected_origins',[])}
  suffixes=rule.get('expected_host_suffixes',[])
  if relation=='outside_reference_origins' and not expected and not suffixes:raise ValueError('Origin rule needs explicit referenced origins or host suffixes')
  observations=[]
  for item in grounded:
   citation=item['citation']
   if citation.get('source')!='url' or rule['anchor_id'] not in item['supported_anchor_ids']:continue
   url=indexed[citation['step_id']].get('public_url');origin=parsed_origin(url)
   authorized=origin in expected or any(origin[1]==suffix.casefold() or origin[1].endswith('.'+suffix.casefold()) for suffix in suffixes)
   observations.append({'url':url,'scheme':origin[0],'hostname':origin[1],'port':origin[2],'relation':'observed_origin_only' if relation=='observe_only' else 'within_reference_origins' if authorized else 'outside_reference_origins','fraud_inferred':False})
  rows.append({'id':rule['id'],'anchor_id':rule['anchor_id'],'reference':rule.get('reference'),'identity_authorization':'not_established' if relation=='observe_only' else 'compared_to_explicit_reference','observations':observations,'met':bool(observations) and all(v['relation']==('observed_origin_only' if relation=='observe_only' else 'outside_reference_origins') for v in observations),'fraud_inferred':False})
 return rows
