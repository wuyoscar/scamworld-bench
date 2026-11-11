"""Resolve an optional, exact-byte catalog version for v1.1 fake elements.

v1.1 specs bind release-relative catalog paths. A bound catalog is read from that path under the release root, else by
file name from v11-inputs/ next to this module, and its sha256 must match the binding; the unbound default is read from
v11-inputs/ against the sha256 pinned here. The public release does not ship v11-inputs/ (see catalog_available).
"""
import hashlib
import json
from pathlib import Path

# The default catalog is a construction-time file, found by this file name in v11-inputs/. It is not part of this release,
# and verify skips the fake-element catalog audit without it.
DEFAULT = 'fake-elements.json'
V11_DIR = Path(__file__).resolve().parent / 'v11-inputs'
V11_DEFAULT_SHA256 = '80931ee48d0c4f7820854bdde3003771348528ed5fd087f399085134ea2c6f6d'

def catalog_available(root, spec):
    """False in the public release, which ships the sites but not the construction-time fake-element catalogs."""
    binding = spec.get('fake_elements_catalog')
    if binding is None:
        return (V11_DIR / Path(DEFAULT).name).is_file()
    relative = Path(binding.get('path', '')) if isinstance(binding, dict) else Path()
    return (Path(root) / relative).is_file() or (V11_DIR / relative.name).is_file()


def load_catalog(root, spec):
    root = Path(root).resolve()
    binding = spec.get('fake_elements_catalog')
    if binding is None:
        raw = (V11_DIR / Path(DEFAULT).name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != V11_DEFAULT_SHA256:
            raise ValueError('v1.1 default catalog changed')
        return json.loads(raw)
    if not isinstance(binding, dict) or set(binding) != {'path', 'sha256'}:
        raise ValueError('catalog binding requires exactly path and sha256')
    relative = Path(binding['path'])
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('catalog must be a release-relative path')
    for path in ((root / relative).resolve(), (V11_DIR / relative.name).resolve()):
        if path.is_file() and (path.is_relative_to(root) or path.is_relative_to(V11_DIR.resolve())):
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() == binding['sha256']:
                return json.loads(raw)
    raise ValueError('catalog binding SHA256 mismatch or catalog missing')
