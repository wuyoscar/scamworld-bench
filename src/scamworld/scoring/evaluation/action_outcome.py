"""Opt-in predicates over executed browser actions and public observations.

The private rule names controls by accessible role/name and exact destination URL.
It never uses source DOM IDs, BrowserGym BIDs in the contract, or answer text.
"""

import html
import re
import unicodedata
from urllib.parse import urlsplit


def _name(value):
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", html.unescape(value))).strip().casefold()


def _url(value):
    if not isinstance(value, str) or not value or value != value.strip() or any(c.isspace() for c in value):
        return False
    try:
        parts = urlsplit(value)
        return (parts.scheme in {"http", "https"} and bool(parts.hostname)
                and not parts.username and not parts.password and not parts.fragment
                and not any(c in value for c in "*\\"))
    except ValueError:
        return False


def validate_action_observations(config):
    """Reject ambiguous private contracts before a run can be scored."""
    if not isinstance(config, list) or not config:
        raise ValueError("required_action_observations must be a nonempty list")
    ids = set()
    for rule in config:
        if not isinstance(rule, dict) or set(rule) - {"id", "controls", "destination_urls", "actions", "transition_window", "public_postcondition"}:
            raise ValueError("Invalid action-observation rule fields")
        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", rule_id) or rule_id in ids:
            raise ValueError("Action-observation rule IDs must be unique simple names")
        ids.add(rule_id)
        controls = rule.get("controls")
        if not isinstance(controls, list) or not controls:
            raise ValueError("Action-observation controls must be a nonempty list")
        for control in controls:
            if (not isinstance(control, dict) or set(control) != {"role", "name"}
                    or not all(isinstance(control[k], str) and control[k].strip() for k in ("role", "name"))):
                raise ValueError("Each action-observation control needs a role and name")
        urls = rule.get("destination_urls")
        if not isinstance(urls, list) or not urls or not all(_url(url) for url in urls) or len(urls) != len(set(urls)):
            raise ValueError("Action-observation destinations must be unique exact HTTP(S) URLs")
        actions = rule.get("actions", ["click", "press"])
        if not isinstance(actions, list) or not actions or len(actions) != len(set(actions)) or set(actions) - {"click", "press"}:
            raise ValueError("Action-observation actions may only be click and press")

        post = rule.get("public_postcondition")
        if post is not None:
            if rule.get('transition_window') is not None or not isinstance(post,dict):
                raise ValueError('Public postcondition cannot combine with delayed window')
            if post.get('version')=='public_anchor_v1':
                if set(post)!={'version','anchor_id','after'} or not all(isinstance(post[k],str) and post[k].strip() for k in ('anchor_id','after')):
                    raise ValueError('Public anchor postcondition needs anchor_id and exact after text')
            elif post.get('version')=='same_public_control_v1':
                if set(post)!={'version','role','before','after','property'} or post['property'] not in ('name','value') or not all(isinstance(post[k],str) and post[k].strip() for k in ('role','before','after')) or post['before']==post['after']:
                    raise ValueError('Invalid same-public-control postcondition')
            else:raise ValueError('Unsupported public postcondition version')
        window = rule.get("transition_window")
        if window is not None:
            if not isinstance(window, dict) or set(window) != {"max_following_steps", "source_urls", "source_quotes"}:
                raise ValueError("transition_window requires max_following_steps, source_urls and source_quotes")
            count = window["max_following_steps"]
            if type(count) is not int or not 1 <= count <= 30:
                raise ValueError("Delayed transition window must contain 1–30 following observations")
            source_urls = window["source_urls"]
            if (not isinstance(source_urls, list) or not source_urls or len(source_urls) > 20
                    or len(source_urls) != len(set(source_urls))
                    or not all(isinstance(u,str) and not any(c.isspace() or c in '*\\' for c in u) and _url(u.split('#',1)[0]) for u in source_urls)):
                raise ValueError("Delayed source URLs must be finite exact HTTP(S) URLs; source fragments are permitted")
            quotes = window["source_quotes"]
            if not isinstance(quotes,list) or not 1 <= len(quotes) <= 10 or not all(isinstance(q,str) and 1 <= len(q.strip()) <= 1200 for q in quotes):
                raise ValueError("Delayed activation requires finite actual source accessibility quotes")


def evaluate_action_observations(config, trace, case_id):
    """All rule groups must have one qualifying action/observation transition."""
    validate_action_observations(config)
    steps = trace.get("steps", [])
    case_matches = trace.get("case_id") == case_id
    results = []
    for rule in config:
        matched_step = None
        rejection_counts = {}
        window = rule.get("transition_window")
        controls = {(_name(c["role"]), _name(c["name"])) for c in rule["controls"]}
        actions = set(rule.get("actions", ["click", "press"]))
        for index, step in enumerate(steps):
            action = step.get("action") or {}
            if action.get("type") not in actions:
                continue

            reason = None
            previous = steps[index - 1] if index else None
            before = (previous or {}).get("observation") or {}
            after = step.get("observation") or {}
            bid = action.get("observed_bid")
            if not case_matches:
                reason = "case_mismatch"
            elif (not previous or type(previous.get("step_id")) is not int
                  or type(step.get("step_id")) is not int
                  or previous["step_id"] >= step["step_id"]):
                reason = "missing_preceding_observation"
            elif previous.get("action", {}).get("type") == "reset" and previous.get("execution") != "succeeded":
                reason = "failed_reset"
            elif not before.get("observation_id") or not after.get("observation_id") or before["observation_id"] == after["observation_id"]:
                reason = "missing_observation_transition"
            elif step.get("before_state_id") != previous.get("after_state_id") or before.get("state_id") != step.get("before_state_id"):
                reason = "disconnected_state"
            elif step.get("execution") != "succeeded" or step.get("error") or (not window and step.get("transition_observed") is not True):
                reason = "action_not_observed_succeeded"
            elif action.get("type") == "press" and action.get("value") not in ("Enter", "Space", " "):
                reason = "unsupported_activation_key"
            elif not isinstance(bid, (str, int)) or isinstance(bid, bool):
                reason = "missing_observed_bid"
            elif not any(str(c.get("bid")) == str(bid) and (_name(c.get("role", "")), _name(c.get("name", ""))) in controls
                         for c in before.get("public_accessibility_controls", []) if isinstance(c, dict)):
                reason = "control_not_observed"
            elif window and (before.get("public_url") not in window["source_urls"] or not all(
                    any(_name(q)==_name(value) for value in
                        [r.get("text","") for r in before.get("public_accessibility_text",[]) if isinstance(r,dict)] +
                        [r.get("name","") for r in before.get("public_accessibility_controls",[]) if isinstance(r,dict)])
                    for q in window["source_quotes"])):
                reason = "source_observation_not_matched"
            elif window:
                destination_step = None
                predecessor = previous
                for candidate in steps[index:index+window["max_following_steps"]+1]:
                    observation = candidate.get("observation") or {}
                    kind = (candidate.get("action") or {}).get("type")
                    if candidate is not step and kind not in {"noop","wait","scroll","browsergym_observation","final_answer"}:
                        break
                    if (candidate.get("execution") != "succeeded" or candidate.get("error")
                            or type(candidate.get("step_id")) is not int
                            or candidate["step_id"] <= predecessor["step_id"]
                            or candidate.get("before_state_id") != predecessor.get("after_state_id")
                            or observation.get("state_id") != candidate.get("after_state_id")
                            or not observation.get("observation_id")
                            or observation["observation_id"] == predecessor.get("observation",{}).get("observation_id")):
                        break
                    if observation.get("public_url") in rule["destination_urls"]:
                        destination_step = candidate["step_id"]
                        break
                    if kind == "final_answer":break
                    predecessor = candidate
                if destination_step is None:reason = "delayed_destination_not_observed"
            elif after.get("public_url") not in rule["destination_urls"]:
                reason = "wrong_destination"
            elif rule.get('public_postcondition'):
                post=rule['public_postcondition']
                if post['version']=='public_anchor_v1':
                    anchor=post['anchor_id'];expected=post['after']
                    def public_anchor(ob):
                        from .observations import node_texts
                        ids={str(n) for n in ob.get('accessibility_anchor_nodes',{}).get(anchor,[])}
                        texts=[text for n in ob.get('public_accessibility_nodes',[]) if not n.get('ignored') and str(n.get('nodeId')) in ids for text in node_texts(n)]
                        return ob.get('accessibility_text_evidence',{}).get(anchor)==expected and expected in texts
                    if before.get('public_url')!=after.get('public_url') or after.get('state_id')!=step.get('after_state_id'):
                        reason='postcondition_observation_disconnected'
                    elif public_anchor(before) or not public_anchor(after):
                        reason='public_postcondition_not_observed'
                    if reason:
                        rejection_counts[reason]=rejection_counts.get(reason,0)+1
                        continue
                    matched_step=step['step_id']
                    break
                prop=post['property']
                # A unique source-observed result control is joined by its actual
                # supplied BID. Contracts never declare ephemeral runtime IDs.
                sources=[c for c in before.get('public_accessibility_controls',[]) if _name(c.get('role'))==_name(post['role']) and c.get(prop)==post['before'] and c.get('bid') is not None]
                if before.get('public_url')!=after.get('public_url') or after.get('state_id')!=step.get('after_state_id'):
                    reason='postcondition_observation_disconnected'
                elif len(sources)!=1:
                    reason='postcondition_source_not_unique'
                elif len([c for c in after.get('public_accessibility_controls',[]) if str(c.get('bid'))==str(sources[0]['bid']) and _name(c.get('role'))==_name(post['role']) and c.get(prop)==post['after']])!=1:
                    reason='public_postcondition_not_observed' 
            if reason:
                rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
            else:
                matched_step = step["step_id"]
                if window:matched_destination_step = destination_step
                break
        row = {"id": rule["id"], "met": matched_step is not None,
               "matched_step_id": matched_step, "rejection_counts": rejection_counts}
        if window:row["matched_destination_step_id"] = matched_destination_step if matched_step is not None else None
        results.append(row)
    return {"status": "met" if all(r["met"] for r in results) else "unmet", "required_groups": results}
