"""Case-id helpers: the single place that knows how case ids are shaped.

Legacy ids: ``candidate-...`` (scam), ``benign-...`` (control), ``<base>--<variant>`` (variant dir).
Current ids: ``<scene>-NN``, ``ok-<scene>-NN``, ``<base>.<variant>``.
Callers must use these helpers instead of splitting/prefix-testing ids themselves.
Pure stdlib, no network; the registry and specs are read lazily and cached (invalidated by file mtime).
"""
import hashlib
import json
import re
from pathlib import Path

from scamworld.paths import RELEASE, TASKS as CASES

REGISTRY = RELEASE / 'registry.json'
NEW_FORM = re.compile(r'^(ok-)?[a-z]+-\d{2}$')

_cache = {}


def _load_json(path):
    path = Path(path)
    try:
        key = (str(path), path.stat().st_mtime_ns)
    except OSError:
        return None
    if key not in _cache:
        for k in [k for k in _cache if k[0] == key[0]]:
            del _cache[k]
        try:
            _cache[key] = json.loads(path.read_text())
        except (OSError, ValueError):
            return None
    return _cache[key]


def _rows(registry=None):
    data = registry if isinstance(registry, dict) else _load_json(registry or REGISTRY)
    return list((data or {}).get('cases') or [])


def _row(case_id, registry=None):
    if isinstance(registry, dict):
        return next((r for r in _rows(registry) if r.get('case_id') == case_id), None)
    path = Path(registry or REGISTRY)
    data = _load_json(path)
    if data is None:
        return None
    key = (str(path), 'index', id(data))
    if key not in _cache:
        for k in [k for k in _cache if k[0] == key[0] and k[1:2] == ('index',)]:
            del _cache[k]
        _cache[key] = {r.get('case_id'): r for r in data.get('cases') or []}
    return _cache[key].get(case_id)


def case_ids(registry=None):
    """Case ids from the registry, in registry order (use this instead of globbing task folders)."""
    return [r['case_id'] for r in _rows(registry) if r.get('case_id')]


def base_of(case_id, registry=None):
    """Base site id of a case id (the id itself for non-variants)."""
    row = _row(case_id, registry)
    if row and row.get('variant_of'):
        return row['variant_of']
    if '--' in case_id:
        return case_id.split('--')[0]
    if '.' in case_id:
        prefix = case_id.split('.')[0]
        if _row(prefix, registry):
            return prefix
    return case_id


def spec_path(case_id):
    return CASES / base_of(case_id) / 'scoring/spec.json'


def is_benign(case_id, registry=None):
    """Benign control? Base case spec flag, else registry row flag, else legacy prefix rule."""
    spec = _load_json(spec_path(case_id))
    if isinstance(spec, dict) and 'benign' in spec:
        return bool(spec['benign'])
    row = _row(base_of(case_id, registry), registry)
    if row and 'benign' in row:
        return bool(row['benign'])
    return case_id.startswith(('benign-', 'ok-'))


def variant_dir_name(base, variant):
    """Directory/case id of a variant of ``base``."""
    return f'{base}.{variant}' if NEW_FORM.match(base) else f'{base}--{variant}'


def is_new_form(case_id):
    """True for renamed ids (``<scene>-NN``, ``ok-<scene>-NN``, with an optional ``.<variant>`` suffix)."""
    return bool(NEW_FORM.match(case_id.split('.')[0]))


def legacy_prefix(case_id):
    """Event prefix a LEGACY dir name implies: 'sw' + trailing digits (<=7), else sha256(name)[:8].
    Renamed ids must carry ``spec.prefix``; deriving one from the new name would change every event id, so refuse."""
    if is_new_form(case_id):
        raise ValueError(f'{case_id}: spec has no "prefix" and the id is a renamed one; pin spec.prefix, never derive it from the dir name')
    m = re.search(r'(\d+)$', case_id)
    tail = m.group(1) if m and len(m.group(1)) <= 7 else hashlib.sha256(case_id.encode()).hexdigest()[:8]
    return 'sw' + tail
