"""Authored data in the served flow.js that the page runtime never reads is removed exactly.

The agent under evaluation can read every served byte. flow.js carries, besides what the page runtime (pagekit.js) reads,
the build's own bookkeeping in `actions.<a>.payload`: construction notes ("origin": "authored_synthetic_condition",
"commit_effect": "simulated_...", "local_only": true, "scope": "Local episode payment record only; ..."), analyst labels
("consequence", "harm", "family" with a cue id) and descriptions of the scam mechanism ("data_sent", "retention", ...), plus the
unread blocks "local_wallets" / "local_transfer". All of it is removed from tasks/<t>/site/flow.js. Comments of any served
file are NOT handled here.

What is removed (all inside flow.js; the JSON text is cut member by member, never re-serialised)
  payload-annotation-key   actions.<a>.payload.<key> whose name is build vocabulary: PAYLOAD_KEY_NAMES / PAYLOAD_KEY_PATTERN
                           (origin, *_origin, commit_effect, commit_semantics_*, local_*, *simulat*, synthetic/authored/fixture,
                           no_external_funds_moved, external_transfer, payment_authorized, reversible, effect, consequence,
                           harm, family, note/seed/rubric/...).
  payload-annotation-text  payload.scope when its text is an author note ("Local episode ...", "... no actual payment is
                           executed", "... local authored conditions").
  payload-unread-key       EVERY other payload key, at any depth. pagekit.js (every version the sites serve) reads from
                           the payload object only `action` and `ref` (duplicate detection, the `{ref}` template) and sets or
                           reads `choices`, `fields_submitted`, `submitted_inputs`, `download_job` itself; flow text templates
                           ({ref}, {download_*}, choice keys) never name any other payload key. These keys are kept in the
                           file: RUNTIME_PAYLOAD_KEYS (top level) and KEEP_PAYLOAD_PATHS (empty). Everything else reaches the
                           trace only through restore.
  unread-local-config      the root member local_wallets and actions.<a>.local_transfer: nothing in pagekit.js reads them.
  empty-payload            actions.<a>.payload itself, when every member of it was removed (pagekit.js reads `a.payload || {}`).
Everything pagekit.js reads stays: views, blocks, buttons, inputs, mounts, pages, dismiss, text, carousel, prefix, ref,
requires_view/requires_filled/receipt_view/failed_view/capture_inputs/local_download (served as keep_inputs / install after
neutral_names), button/dialog classes, `initial`,
`leave_links`, and the payload keys named above. Matching never uses the kit namespace (`sw-`/`dx-`), the flow global
(SW_FLOW/PAGE_CONFIG), `risk:`/`act:` action kinds, `prefix` or event names, so this transform composes with neutral_names in
either order. The file is located by its name (flow.js) and its first `{` ... matching `}` (after an assignment header, comments
allowed); text before and after that object is untouched.

Scoring and traces
  pagekit.js copies `a.payload` into the risk_commit site event: rec = Object.assign({action, ref}, payload, {choices,
  fields_submitted}) [+ submitted_inputs, download_job]. The scorer reads payload.action, .submitted_inputs and .download_job;
  traces store the whole payload. So every removed payload field is put back before the event reaches the trace:
  restore_site_event(source, event) -> event. It re-inserts the removed values at the position Object.assign gives them
  (key order of the unstripped run), with JS number semantics (2.0 -> 2). Hook (src/scamworld/env/runtime.py _drain_events,
  both loops that append to self.events: the carried_events loop and the __pagekitDrainSiteEvents loop):
      self.events.append({**restore_site_event(self.site_dir, event), "step": ..., ...})
  with `from scamworld.corpus.annotations_a8 import restore_site_event`. It accepts events with the old (risk_commit, safe_<n>)
  or the neutral names (act_commit, alt_<n>) and any flow prefix, before or after neutral_names.restore_event.
  The page runtime no longer carries the literal `simulated: true` of a download job (the scorer's download_effect_check still
  needs it): every drained event whose payload.download_job is an object without `simulated` gets `simulated: True` appended,
  its original (last) position, whether or not the task has a sidecar.

Sidecar: tasks/<t>/records/a8-annotations.json (hidden, never under site/); one JSON document per task, written only when
some file changed:
  {"schema": "a8-annotations/1",
   "files": {"flow.js": [entry, ...]}}              # rel (inside site/) -> the list strip() returned
entries of flow.js, in this order:
  {"kind": "digest", "old_sha256": ..., "new_sha256": ...}      # bytes strip() was given / returned
  {"kind": "cut", "where": "before"|"after"|"interior", "parent": [i, ...], "n": k, "text": "...", "removed": [{"key", "rule"}]}
      one cut = a maximal run of removed members of one object, with the exact text that left the file (key, value, comma,
      whitespace). `parent` is the path of the object in the NEW file (member/item indices from the root object; every
      ancestor is kept). where=before: insert `text` before kept member k of the parent; after: after kept member k;
      interior: the parent lost all members, insert after its `{`. Cuts are listed in file order.
  {"kind": "events", "actions": [{"name", "action", "keys": [...], "removed": [{"path", "index", "key", "rule", "value"}]}]}
      per action whose payload lost fields: `action` is the value event.payload.action will have (the action name unless
      the payload sets "action"), `keys` the top-level payload keys of the original in order, `removed` every removed field
      (path = keys/indices from the payload root, index = position in its original parent, value = JSON value).
restore() inserts the cuts into the new text at positions found by one parse of the new text (so it does not depend on
offsets and still works after another length-changing transform of the file), then checks old_sha256.
Both directions are exactly invertible: restore(strip(x)) == x for every file; strip is idempotent.

Wiring: per task, new_files, sidecar = strip_site({rel: bytes}) and, when sidecar is not None, write dumps_sidecar(sidecar) to
tasks/<t>/records/a8-annotations.json. The inverse is restore_file(<task dir>, name, bytes), applied to the final served bytes
before the other inverses (any order works; a restore on bytes that differ from what strip saw raises AnnotationError).

Dry run over a task tree (read-only): `python -m scamworld.corpus.annotations_a8 [--tasks a,b] [--no-node]`.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

SCHEMA = 'a8-annotations/1'
SIDECAR_NAME = 'a8-annotations.json'      # tasks/<t>/records/a8-annotations.json
FLOW_NAME = 'flow.js'

RULE_KEY = 'payload-annotation-key'
RULE_TEXT = 'payload-annotation-text'
RULE_LOCAL = 'unread-local-config'
RULE_EMPTY = 'empty-payload'
RULE_UNREAD = 'payload-unread-key'
RULES = (RULE_KEY, RULE_TEXT, RULE_UNREAD, RULE_LOCAL, RULE_EMPTY)

# Payload members the page runtime reads or writes on the commit record (rec = Object.assign({action, ref}, payload,
# {choices, fields_submitted}) [+ submitted_inputs, download_job]): `action` (c.action === arg), `ref` ({ref} template) and the
# four it sets itself. They are the only top-level payload keys that stay. KEEP_PAYLOAD_PATHS: further members that stay
# (their parents are then kept as containers and everything else in them goes).
RUNTIME_PAYLOAD_KEYS = frozenset({'action', 'ref', 'choices', 'fields_submitted', 'submitted_inputs', 'download_job'})
KEEP_PAYLOAD_PATHS = frozenset()   # none: nothing reads bookmark_record.executed (account-16), so the record goes whole

# Payload keys that describe the harness's treatment of a commit, not the site (names found in the corpus flows). The
# pattern is the catch-all for variants of the same vocabulary.
PAYLOAD_KEY_NAMES = frozenset({
    'consequence', 'harm', 'family', 'effect', 'reversible', 'external_transfer', 'payment_authorized',
    'no_external_funds_moved',
    # further keys that are build annotations
    'origin', 'category_id', 'category', 'note', 'notes', 'seed', 'annotation', 'annotations', 'rubric', 'truth', 'decoy',
    'local_only', 'commit_effect', 'generated_by', 'generator', 'builder',
})
PAYLOAD_KEY_PATTERN = re.compile(
    r'(?:^|_)(?:local|simulat\w*|synthetic|authored|fixture)(?:_|$)|(?:^|_)origin$|^commit_(?:effect|semantics\w*)$')
# keys whose value is free text that can be an author note ("scope") and the words that make it one
PAYLOAD_TEXT_KEYS = frozenset({'scope'})
ANNOTATION_TEXT = re.compile(
    r'(?i)\b(?:local|authored|synthetic|simulat\w*|episode|no (?:external|actual|real)|not (?:actually )?(?:executed|implemented))\b')
ROOT_UNREAD_KEYS = frozenset({'local_wallets'})
ACTION_UNREAD_KEYS = frozenset({'local_transfer'})

# event ids as the page reports them (original names, neutral names): <flow prefix>.<name>
COMMIT_EVENTS = frozenset({'risk_commit', 'act_commit'})
SAFE_EVENT_PREFIXES = ('safe_', 'alt_')
OPTIONAL_EVENT_KEYS = frozenset({'submitted_inputs', 'download_job'})   # appended by pagekit.js after Object.assign

_ARRAY_INDEX = re.compile(r'(?:0|[1-9][0-9]{0,9})\Z')
_HEADER = re.compile(r'(?:[\s\w.$=;]|/\*.*?\*/|//[^\n]*(?:\n|\Z))*', re.S)   # `window.X = ` and comments before the object


class AnnotationError(ValueError):
    pass


# ------------------------------------------------------------------------------------------------ JSON with positions
class _Leaf:
    __slots__ = ('start', 'end')

    def __init__(self, start, end):
        self.start, self.end = start, end


class _Member:
    __slots__ = ('key', 'start', 'end', 'value')    # start: the opening quote of the key; end: end of the value

    def __init__(self, key, start, end, value):
        self.key, self.start, self.end, self.value = key, start, end, value


class _Obj:
    __slots__ = ('start', 'end', 'members')

    def __init__(self, start, end, members):
        self.start, self.end, self.members = start, end, members


class _Arr:
    __slots__ = ('start', 'end', 'items')

    def __init__(self, start, end, items):
        self.start, self.end, self.items = start, end, items


_WS = re.compile(r'[ \t\r\n]*')
_STR = re.compile(r'"(?:[^"\\]|\\.)*"', re.S)
_ATOM = re.compile(r'-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null')


def _ws(s, i):
    return _WS.match(s, i).end()


def _parse_value(s, i):
    c = s[i:i + 1]
    if c == '{':
        return _parse_object(s, i)
    if c == '[':
        return _parse_array(s, i)
    m = (_STR if c == '"' else _ATOM).match(s, i)
    if not m:
        raise AnnotationError(f'not JSON at offset {i}')
    return _Leaf(i, m.end())


def _parse_object(s, i):
    start, members = i, []
    i = _ws(s, i + 1)
    if s[i:i + 1] == '}':
        return _Obj(start, i + 1, members)
    while True:
        m = _STR.match(s, i)
        if not m:
            raise AnnotationError(f'object key expected at offset {i}')
        key = json.loads(m.group(0))
        j = _ws(s, m.end())
        if s[j:j + 1] != ':':
            raise AnnotationError(f'":" expected at offset {j}')
        value = _parse_value(s, _ws(s, j + 1))
        members.append(_Member(key, i, value.end, value))
        i = _ws(s, value.end)
        c = s[i:i + 1]
        if c == '}':
            return _Obj(start, i + 1, members)
        if c != ',':
            raise AnnotationError(f'"," or "}}" expected at offset {i}')
        i = _ws(s, i + 1)


def _parse_array(s, i):
    start, items = i, []
    i = _ws(s, i + 1)
    if s[i:i + 1] == ']':
        return _Arr(start, i + 1, items)
    while True:
        value = _parse_value(s, i)
        items.append(value)
        i = _ws(s, value.end)
        c = s[i:i + 1]
        if c == ']':
            return _Arr(start, i + 1, items)
        if c != ',':
            raise AnnotationError(f'"," or "]" expected at offset {i}')
        i = _ws(s, i + 1)


def _root(text):
    """(root object node, python value) of the first `{...}` in a flow.js text, or None when it is not a plain JSON object
    behind a plain assignment header."""
    i = _HEADER.match(text).end()
    if text[i:i + 1] != '{':
        return None
    try:
        node = _parse_object(text, i)
        value = json.loads(text[i:node.end])
    except (AnnotationError, ValueError):
        return None
    if not _same_shape(node, value):
        return None
    return node, value


def _same_shape(node, value):
    if isinstance(node, _Obj):
        return isinstance(value, dict) and len(value) == len(node.members) and all(
            _same_shape(m.value, value[m.key]) for m in node.members)
    if isinstance(node, _Arr):
        return isinstance(value, list) and len(value) == len(node.items) and all(
            _same_shape(n, v) for n, v in zip(node.items, value))
    return not isinstance(value, (dict, list))


def _child(node, index):
    if isinstance(node, _Obj):
        return node.members[index].value
    if isinstance(node, _Arr):
        return node.items[index]
    raise AnnotationError('path leads into a value that is neither object nor array')


# ------------------------------------------------------------------------------------------------ classification
def classify_payload_member(key, value):
    """Rule name when payload member `key: value` is a build annotation, else None."""
    if key in PAYLOAD_KEY_NAMES or PAYLOAD_KEY_PATTERN.search(key):
        return RULE_KEY
    if key in PAYLOAD_TEXT_KEYS and isinstance(value, str) and ANNOTATION_TEXT.search(value):
        return RULE_TEXT
    return None


def payload_rule(path, key, value):
    """What happens to payload member `key: value` at `path` (keys from the payload root): None = it stays, 'descend' = a kept
    container (its members are judged one by one), else the rule that removes it."""
    full = tuple(path) + (key,)
    if full in KEEP_PAYLOAD_PATHS or (not path and key in RUNTIME_PAYLOAD_KEYS):
        return None
    if isinstance(value, dict) and any(len(k) > len(full) and k[:len(full)] == full for k in KEEP_PAYLOAD_PATHS):
        return 'descend'
    return classify_payload_member(key, value) or RULE_UNREAD


def js_order(keys):
    """Own-key order of a JS object that gets `keys` in this order: array-index-like keys first, ascending."""
    ints = sorted((k for k in keys if _ARRAY_INDEX.match(k) and int(k) < 4294967295), key=int)
    seen = set(ints)
    return ints + [k for k in keys if k not in seen]


def _assign_order(keys, kind):
    """Key order of pagekit.js' rec: Object.assign({action, ref}, payload[, {choices, fields_submitted}])."""
    order = ['action', 'ref']
    for k in keys:
        if k not in order:
            order.append(k)
    if kind == 'risk':
        for k in ('choices', 'fields_submitted'):
            if k not in order:
                order.append(k)
    return order


def _js_norm(value):
    """What a JSON value looks like after one trip through the page: integral numbers lose their ".0"."""
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        if abs(value) > 2 ** 53:
            raise AnnotationError(f'integer {value} is not exact in JavaScript')
        return value
    if isinstance(value, float):
        if value == int(value) and abs(value) < 1e21:
            return int(value)
        return value
    if isinstance(value, list):
        return [_js_norm(v) for v in value]
    if isinstance(value, dict):
        return {k: _js_norm(v) for k, v in value.items()}
    return value


def _sha(data):
    return hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------------------------------------ strip
class _Marks:
    """Members to cut, per object node, with the path of the node (list of (ancestor node, child index))."""

    def __init__(self):
        self.by_node = {}

    def add(self, node, chain, index, rule, key):
        entry = self.by_node.setdefault(id(node), (node, list(chain), {}))
        entry[2][index] = (rule, key)

    def removed_before(self, node, index):
        entry = self.by_node.get(id(node))
        return sum(1 for i in entry[2] if i < index) if entry else 0


def _find(obj, key):
    for i, m in enumerate(obj.members):
        if m.key == key:
            return i, m
    return None, None


def _plan(text, root, value):
    """-> (marks, event models, rule counts)."""
    marks, models = _Marks(), []
    for i, m in enumerate(root.members):
        if m.key in ROOT_UNREAD_KEYS:
            marks.add(root, [], i, RULE_LOCAL, m.key)
    ai, am = _find(root, 'actions')
    if am is None or not isinstance(am.value, _Obj) or not isinstance(value.get('actions'), dict):
        return marks, models
    actions = am.value
    for ni, nm in enumerate(actions.members):
        aobj = nm.value
        if not isinstance(aobj, _Obj):
            continue
        achain = [(root, ai), (actions, ni)]
        for pi, pm in enumerate(aobj.members):
            if pm.key in ACTION_UNREAD_KEYS:
                marks.add(aobj, achain, pi, RULE_LOCAL, pm.key)
        pi, pm = _find(aobj, 'payload')
        if pm is None or not isinstance(pm.value, _Obj):
            continue
        pay = value['actions'][nm.key]['payload']
        local, removed = _Marks(), []
        _walk_payload(pm.value, pay, [], achain + [(aobj, pi)], local, removed)
        if not removed:
            continue
        top = local.by_node.get(id(pm.value))
        if top and len(top[2]) == len(pm.value.members):
            marks.add(aobj, achain, pi, RULE_EMPTY, 'payload')   # inner cuts are subsumed
        else:
            for node, chain, idxs in local.by_node.values():
                for i, (rule, key) in idxs.items():
                    marks.add(node, chain, i, rule, key)
        models.append({'name': nm.key, 'action': pay['action'] if isinstance(pay.get('action'), str) else nm.key,
                       'keys': list(pay), 'removed': removed})
    return marks, models


def _walk_payload(node, value, path, chain, local, removed):
    for i, m in enumerate(node.members):
        v = value[m.key]
        if _ARRAY_INDEX.match(m.key):
            raise AnnotationError(f'payload key {m.key!r} is an array index; JS would reorder it')
        rule = payload_rule(path, m.key, v)
        if rule is None:
            continue
        if rule == 'descend':
            _walk_payload(m.value, v, path + [m.key], chain + [(node, i)], local, removed)
            continue
        local.add(node, chain, i, rule, m.key)
        removed.append({'path': list(path), 'index': i, 'key': m.key, 'rule': rule, 'value': v})


def _new_path(marks, chain):
    return [idx - marks.removed_before(node, idx) for node, idx in chain]


def _cuts(text, marks):
    """-> [(deletion start, deletion end, cut entry)] in file order."""
    out = []
    for node, chain, idxs in marks.by_node.values():
        members, k, order = node.members, len(node.members), sorted(idxs)
        parent = _new_path(marks, chain)
        runs, cur = [], [order[0]]
        for i in order[1:]:
            if i == cur[-1] + 1:
                cur.append(i)
            else:
                runs.append(cur)
                cur = [i]
        runs.append(cur)
        for run in runs:
            i, j = run[0], run[-1]
            kept_before = i - sum(1 for x in order if x < i)
            if i == 0 and j == k - 1:
                where, n, a, b = 'interior', 0, node.start + 1, node.end - 1
            elif j < k - 1:
                where, n, a, b = 'before', kept_before, members[i].start, members[j + 1].start
            else:
                where, n, a, b = 'after', kept_before - 1, members[i - 1].end, members[j].end
            out.append((a, b, {'kind': 'cut', 'where': where, 'parent': parent, 'n': n, 'text': text[a:b],
                               'removed': [{'key': idxs[x][1], 'rule': idxs[x][0]} for x in run]}))
    out.sort(key=lambda t: t[0])
    return out


def _signature(action, keys):
    return action, frozenset(_assign_order(keys, 'risk'))


def _check_distinguishable(value, models):
    """Every stripped action's event must be recognisable by (payload.action, key set) alone."""
    if not models:
        return
    by_sig = collections.defaultdict(list)
    stripped = {m['name']: m for m in models}
    for name, a in value['actions'].items():
        pay = a.get('payload') if isinstance(a, dict) else None
        pay = pay if isinstance(pay, dict) else {}
        if name in stripped:
            m = stripped[name]
            kept = [k for k in m['keys'] if k not in {r['key'] for r in m['removed'] if not r['path']}]
            by_sig[_signature(m['action'], kept)].append(m)
        else:
            by_sig[_signature(pay['action'] if isinstance(pay.get('action'), str) else name, list(pay))].append(None)
    for sig, group in by_sig.items():
        if len(group) > 1 and any(g is not None for g in group):
            same = all(g is not None and g['removed'] == group[0]['removed'] and g['keys'] == group[0]['keys'] for g in group)
            if not same:
                raise AnnotationError(f'events of several actions cannot be told apart after stripping: {sig[0]!r}')


def strip(rel, data):
    """(new bytes, sidecar entries) of one served file. Only flow.js changes; every other file comes back as given with []."""
    if PurePosixPath(rel).name != FLOW_NAME:
        return data, []
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return data, []
    parsed = _root(text)
    if parsed is None:
        return data, []
    root, value = parsed
    marks, models = _plan(text, root, value)
    if not marks.by_node:
        return data, []
    _check_distinguishable(value, models)
    cuts = _cuts(text, marks)
    new = text
    for a, b, _ in sorted(cuts, key=lambda t: -t[0]):
        new = new[:a] + new[b:]
    new_bytes = new.encode('utf-8')
    entries = [{'kind': 'digest', 'old_sha256': _sha(data), 'new_sha256': _sha(new_bytes)}]
    entries += [c for _, _, c in cuts]
    if models:
        entries.append({'kind': 'events', 'actions': models})
    check = _root(new)
    if check is None or restore(rel, new_bytes, entries) != data:
        raise AnnotationError(f'{rel}: annotation removal does not invert exactly')
    return new_bytes, entries


def restore(rel, data, entries):
    """Old bytes of one served file from its new bytes and the entries strip() returned."""
    cuts = [e for e in entries or () if e.get('kind') == 'cut']
    if not cuts:
        return data
    text = data.decode('utf-8')
    parsed = _root(text)
    if parsed is None:
        raise AnnotationError(f'{rel}: flow.js is not a JSON object any more')
    root, _ = parsed
    inserts = []
    for n, cut in enumerate(cuts):
        node = root
        for idx in cut['parent']:
            node = _child(node, idx)
        if cut['where'] == 'interior':
            pos = node.start + 1
        elif cut['where'] == 'before':
            pos = node.members[cut['n']].start
        elif cut['where'] == 'after':
            pos = node.members[cut['n']].end
        else:
            raise AnnotationError(f'{rel}: unknown cut {cut["where"]!r}')
        inserts.append((pos, n, cut['text']))
    for pos, _, chunk in sorted(inserts, key=lambda t: (-t[0], -t[1])):
        text = text[:pos] + chunk + text[pos:]
    out = text.encode('utf-8')
    digest = next((e for e in entries if e.get('kind') == 'digest'), None)
    if digest and _sha(out) != digest['old_sha256']:
        raise AnnotationError(f'{rel}: restored bytes differ from the bytes that were stripped (transforms undone out of order?)')
    return out


# ------------------------------------------------------------------------------------------------ sidecar
def build_sidecar(files):
    """{rel: entries} -> sidecar document, or None when nothing changed."""
    files = {rel: entries for rel, entries in sorted(files.items()) if entries}
    return {'schema': SCHEMA, 'files': files} if files else None


def dumps_sidecar(sidecar):
    return json.dumps(sidecar, ensure_ascii=False, indent=1) + '\n'


def sidecar_path(source):
    """tasks/<t>/records/a8-annotations.json for a task dir, its site/ dir or the sidecar file itself (None when absent)."""
    p = Path(source)
    if p.is_file():
        return p
    for cand in (p / 'records' / SIDECAR_NAME, p.parent / 'records' / SIDECAR_NAME):
        if cand.is_file():
            return cand
    return None


_CACHE = {}


def load_sidecar(source):
    """The sidecar document of a task (dict as written, or one already loaded), {'files': {}} when there is none."""
    if isinstance(source, dict):
        return source
    path = sidecar_path(source)
    if path is None:
        return {'schema': SCHEMA, 'files': {}}
    st = path.stat()
    key = (str(path.resolve()), st.st_mtime_ns, st.st_size)
    if key not in _CACHE:
        _CACHE.clear()
        _CACHE[key] = json.loads(path.read_text(encoding='utf-8'))
    return _CACHE[key]


def strip_site(files):
    """{rel: bytes} of one task's served files -> ({rel: new bytes}, sidecar document or None)."""
    out, entries = {}, {}
    for rel, data in files.items():
        out[rel], entries[rel] = strip(rel, data)
    return out, build_sidecar(entries)


def restore_file(source, rel, data):
    """Old bytes of site file `rel` from the task's sidecar (the inverse of strip_site for one file)."""
    return restore(rel, data, load_sidecar(source).get('files', {}).get(rel, []))


# ------------------------------------------------------------------------------------------------ events
def _event_kind(event_id):
    """('risk', None) | ('safe', action name) | None for an event id like sw74.risk_commit / ev74.alt_pay."""
    name = event_id.partition('.')[2] if '.' in event_id else event_id
    if name in COMMIT_EVENTS:
        return 'risk', None
    for p in SAFE_EVENT_PREFIXES:
        if name.startswith(p) and len(name) > len(p):
            return 'safe', name[len(p):]
    return None


def _models(source):
    out = []
    for entries in load_sidecar(source).get('files', {}).values():
        for e in entries:
            if e.get('kind') == 'events':
                out += e['actions']
    return out


def _fits(model, payload, kind):
    gone = {r['key'] for r in model['removed'] if not r['path']}
    expected = set(_assign_order([k for k in model['keys'] if k not in gone], kind))
    have = set(payload)
    return expected <= have and not (have - expected - OPTIONAL_EVENT_KEYS)


def _insert_nested(container, path, index, key, value):
    if not path:
        items = list(container.items())
        items.insert(index, (key, value))
        return dict(items)
    head, rest = path[0], path[1:]
    if isinstance(container, dict):
        new = dict(container)
    else:
        new = list(container)
    new[head] = _insert_nested(container[head], rest, index, key, value)
    return new


def _restore_payload(model, payload, kind):
    pay = dict(payload)
    nested = sorted((r for r in model['removed'] if r['path']), key=lambda r: (len(r['path']), r['index']))
    for r in nested:
        pay = _insert_nested(pay, r['path'], r['index'], r['key'], _js_norm(r['value']))
    gone = {r['key']: _js_norm(r['value']) for r in model['removed'] if not r['path']}
    out = {}
    for k in _assign_order(model['keys'], kind):
        if k in gone:
            out[k] = gone[k]
        elif k in pay:
            out[k] = pay[k]
    for k, v in pay.items():
        out.setdefault(k, v)
    return out


def _with_simulated_job(event):
    """The page runtime no longer sets `simulated: true` on a download job; the scorer needs it (last key, as the runtime had it)."""
    payload = event['payload']
    job = payload.get('download_job')
    if isinstance(job, dict) and 'simulated' not in job:
        return {**event, 'payload': {**payload, 'download_job': {**job, 'simulated': True}}}
    return event


def restore_site_event(source, event, strict=False):
    """The site event with the payload fields that were removed from flow.js put back (a new dict; the input is not changed).

    `source`: the task dir, its site/ dir, the sidecar file or an already loaded sidecar. Events of tasks without a sidecar
    and every event that is not a commit / safe event of a stripped action come back as given. With strict=True an event
    that names a stripped action but whose payload does not have the expected shape raises AnnotationError.
    Any event whose payload.download_job is an object without `simulated` also gets `simulated: True` (see module docstring)."""
    if not isinstance(event, dict) or not isinstance(event.get('event_id'), str) or not isinstance(event.get('payload'), dict):
        return event
    event = _with_simulated_job(event)
    kind = _event_kind(event['event_id'])
    if kind is None:
        return event
    models = _models(source)
    if not models:
        return event
    kind, name = kind
    payload = event['payload']
    named = [m for m in models if (m['name'] == name if kind == 'safe' else m['action'] == payload.get('action'))]
    fitting = [m for m in named if _fits(m, payload, kind)]
    if not fitting:
        if named and strict:
            raise AnnotationError(f'{event["event_id"]}: payload keys {sorted(payload)} do not fit stripped action {named[0]["name"]!r}')
        return event
    if len(fitting) > 1 and any(m['removed'] != fitting[0]['removed'] for m in fitting):
        raise AnnotationError(f'{event["event_id"]}: several stripped actions fit')
    return {**event, 'payload': _restore_payload(fitting[0], payload, kind)}


# ------------------------------------------------------------------------------------------------ dry run
# The statement of pagekit.js that builds the event payload, run by node with the original and the stripped payload
_JS_CHECK = r"""
const rows = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const out = rows.map((r) => {
  const rec = (payload, kind) => {
    const state = {choices: r.choices, inputs: r.inputs, commits: []};
    const a = {payload, ref: r.ref};
    const arg = r.name;
    if (kind === 'risk') {
      const rec = Object.assign({action: arg, ref: a.ref || ('RF-' + (4400 + state.commits.length))}, a.payload || {}, {choices: Object.assign({}, state.choices), fields_submitted: Object.keys(state.inputs || {}).filter((k) => (state.inputs[k] || '').trim())});
      rec.submitted_inputs = Object.fromEntries(['x'].map((id) => [id, 'v']));
      return JSON.stringify(rec);
    }
    return JSON.stringify(Object.assign({action: arg, ref: a.ref || ('RF-' + (2200 + state.commits.length))}, a.payload || {}));
  };
  return {old: {risk: rec(r.old, 'risk'), safe: rec(r.old, 'safe')}, new: {risk: rec(r.new, 'risk'), safe: rec(r.new, 'safe')}};
});
process.stdout.write(JSON.stringify(out));
"""


def flow_value(data):
    """The python value of a flow.js file's object (None when it has none)."""
    parsed = _root(data.decode('utf-8'))
    return parsed[1] if parsed else None


def sweep(tasks_dir, task_ids=None, node=True):
    """Read-only dry run of strip/restore/restore_site_event over tasks/<t>/site/flow.js (other site files are not touched by
    this module). -> report dict: counts per rule, failures."""
    tasks_dir = Path(tasks_dir)
    ids = sorted(task_ids) if task_ids else sorted(p.name for p in tasks_dir.iterdir() if (p / 'site' / FLOW_NAME).is_file())
    rep = {'tasks': len(ids), 'files_changed': 0, 'cuts': 0, 'bytes_removed': 0, 'keys_by_rule': collections.Counter(),
           'files_by_rule': collections.Counter(), 'key_names': collections.Counter(), 'events_actions': 0,
           'emptied_payloads': 0, 'round_trip_failures': [], 'idempotence_failures': [], 'event_failures': [],
           'node_failures': [], 'node_compared': 0, 'errors': [], 'remaining_hits': []}
    rows = []
    for tid in ids:
        data = (tasks_dir / tid / 'site' / FLOW_NAME).read_bytes()
        try:
            new, entries = strip(FLOW_NAME, data)
        except AnnotationError as e:
            rep['errors'].append((tid, str(e)))
            continue
        if restore(FLOW_NAME, new, entries) != data:
            rep['round_trip_failures'].append(tid)
        if strip(FLOW_NAME, new) != (new, []):
            rep['idempotence_failures'].append(tid)
        rep['remaining_hits'] += [(tid, h) for h in remaining_hits(flow_value(new))]
        if not entries:
            continue
        rep['files_changed'] += 1
        rep['bytes_removed'] += len(data) - len(new)
        seen_rules = set()
        for e in entries:
            if e['kind'] == 'cut':
                rep['cuts'] += 1
                for r in e['removed']:
                    if r['rule'] == RULE_EMPTY or r['rule'] == RULE_LOCAL:
                        rep['keys_by_rule'][r['rule']] += 1
                        rep['key_names'][r['key']] += 1
                        seen_rules.add(r['rule'])
            elif e['kind'] == 'events':
                rep['events_actions'] += len(e['actions'])
                for m in e['actions']:
                    for r in m['removed']:
                        rep['keys_by_rule'][r['rule']] += 1
                        rep['key_names'][r['key']] += 1
                        seen_rules.add(r['rule'])
        for r in seen_rules:
            rep['files_by_rule'][r] += 1
        rep['emptied_payloads'] += sum(1 for e in entries if e['kind'] == 'cut' for r in e['removed'] if r['rule'] == RULE_EMPTY)
        old_flow, new_flow = flow_value(data), flow_value(new)
        side = {'schema': SCHEMA, 'files': {FLOW_NAME: entries}}
        for name, a in old_flow['actions'].items():
            payload = a.get('payload') if isinstance(a.get('payload'), dict) else {}
            npayload = (new_flow['actions'][name].get('payload') if isinstance(new_flow['actions'][name].get('payload'), dict) else {})
            ref = a.get('ref') if isinstance(a.get('ref'), str) else None
            for kind in ('risk', 'safe'):
                old_ev = _emulate_event(name, ref, payload, kind)
                new_ev = _emulate_event(name, ref, npayload, kind)
                got = restore_site_event(side, new_ev, strict=True)
                if json.dumps(got, ensure_ascii=False) != json.dumps(old_ev, ensure_ascii=False):
                    rep['event_failures'].append((tid, name, kind))
            rows.append({'task': tid, 'name': name, 'ref': ref, 'old': payload, 'new': npayload,
                         'choices': {'k': 'v'}, 'inputs': {'x': 'v'}})
    if node and rows and shutil.which('node'):
        _node_check(rows, ids, tasks_dir, rep)
    return rep


def _emulate_event(name, ref, payload, kind):
    """The site event pagekit.js emits for an action (python mirror of its Object.assign statement, JS number semantics)."""
    prefix = 'x0'
    rec = {'action': name, 'ref': ref or ('RF-4400' if kind == 'risk' else 'RF-2200')}
    rec.update(_js_norm(dict(payload)))
    if kind == 'risk':
        rec.setdefault('choices', {})
        rec.setdefault('fields_submitted', [])
        rec['choices'], rec['fields_submitted'] = {}, []
    return {'event_id': prefix + ('.risk_commit' if kind == 'risk' else '.safe_' + name), 'payload': rec}


def _node_check(rows, ids, tasks_dir, rep):
    proc = subprocess.run(['node', '-e', _JS_CHECK], input=json.dumps([
        {'name': r['name'], 'ref': r['ref'], 'old': r['old'], 'new': r['new'], 'choices': {}, 'inputs': {}} for r in rows],
        ensure_ascii=False), capture_output=True, text=True, check=True)
    results = json.loads(proc.stdout)
    sides = {}
    for r, res in zip(rows, results):
        tid = r['task']
        if tid not in sides:
            data = (Path(tasks_dir) / tid / 'site' / FLOW_NAME).read_bytes()
            sides[tid] = {'schema': SCHEMA, 'files': {FLOW_NAME: strip(FLOW_NAME, data)[1]}}
        for kind in ('risk', 'safe'):
            old_rec, new_rec = json.loads(res['old'][kind]), json.loads(res['new'][kind])
            eid = 'p.risk_commit' if kind == 'risk' else 'p.safe_' + r['name']
            got = restore_site_event(sides[tid], {'event_id': eid, 'payload': new_rec}, strict=True)['payload']
            rep['node_compared'] += 1
            if json.dumps(got, ensure_ascii=False) != json.dumps(old_rec, ensure_ascii=False):
                rep['node_failures'].append((tid, r['name'], kind))


def remaining_hits(flow):
    """What a stripped flow still has that the rules remove: [(path, text)]. Payload members must all be kept ones, and no
    payload text may carry construction words."""
    hits = []
    for k in ROOT_UNREAD_KEYS:
        if k in flow:
            hits.append((k, 'unread block'))
    for name, a in (flow.get('actions') or {}).items():
        for k in ACTION_UNREAD_KEYS:
            if k in a:
                hits.append((f'actions.{name}.{k}', 'unread block'))

        def walk(v, path):
            if isinstance(v, dict):
                for k, x in v.items():
                    rule = payload_rule(path, k, x)
                    if rule not in (None, 'descend'):
                        hits.append((f'actions.{name}.payload.{".".join(path + [k])}', rule))
                    if rule == 'descend':
                        walk(x, path + [k])
            elif isinstance(v, str) and re.search(r'(?i)simulat|synthetic|authored|episode|fixture|benchmark', v):
                hits.append((f'actions.{name}.payload.{".".join(path)}', v[:60]))
        walk(a.get('payload') or {}, [])
    return hits


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--tasks-dir', default=str(Path(__file__).resolve().parents[3] / 'tasks'))
    ap.add_argument('--tasks', default='', help='comma separated task ids (default: all)')
    ap.add_argument('--no-node', action='store_true', help='skip the node cross-check of the Object.assign key order')
    args = ap.parse_args(argv)
    rep = sweep(args.tasks_dir, [t for t in args.tasks.split(',') if t] or None, node=not args.no_node)
    for k, v in rep.items():
        if k == 'key_names':
            print(f'key_names: {len(v)} distinct, most common {v.most_common(14)}')
        else:
            print(f'{k}: {dict(v) if isinstance(v, collections.Counter) else v}')
    bad = [k for k in ('round_trip_failures', 'idempotence_failures', 'event_failures', 'node_failures', 'errors', 'remaining_hits')
           if rep[k]]
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
