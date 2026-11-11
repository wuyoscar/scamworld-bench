"""Validate byte-identical reuse of an image from a local captured MIME part.

This is not an image generator. Reuse supplies visual material only, never
evidence that the target site's endorsement, licence or other claim is true.
"""
import hashlib
import json
from pathlib import Path
import re

from scamworld.corpus.layout import new_relative as layout_new, old_relative
from scamworld.corpus.neutral_names import served_file
from scamworld.paths import RELEASE, TASKS as CAPTURE_CASES
# Manifest of the first task set with the digest of every capture file (restoration.json and the original parts). Only
# the donor checks at the end of validate_reuse read it; it is not shipped, so an image that reaches them fails
# (FileNotFoundError). Exported images are accepted before that by public_manifest_binds, and images of tasks renamed
# after their review by frozen_receipt_binds.
FREEZE_MANIFEST = RELEASE / 'freeze-2026-10-18/freeze-manifest.json'
FREEZE_SHA256 = '812a11ab8cc6001e18d3feaad3af7921078281c7f97fa02904c7421fe627c1b5'
MIMES = {'image/png', 'image/jpeg', 'image/webp', 'image/gif', 'image/avif'}
SCOPE = 'visual_design_only_not_target_truth_or_claim_verification'

def require(ok, message):
    if not ok:
        raise ValueError(message)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def frozen_receipt_binds(local_image, image):
    """Tasks that were renamed after their images were reviewed: donor ids, restoration bytes and dataset paths changed
    with the rename, so the donor checks below cannot run on them. The task's admission record (freeze_transform) binds the
    reviewed bytes from before the rename (old_manifest) and the current bytes (case_hashes).
    Accept when the image file is bound by the record, equals the declared image (and, for donor reuse, the declared donor
    original) and was an asset file of the task before the rename."""
    try:
        p = Path(local_image).resolve()
        cases = CAPTURE_CASES.resolve()
        if not p.is_relative_to(cases):
            return False
        case = cases / p.relative_to(cases).parts[0]
        rec = json.loads((case / 'records/admission.json').read_text())
        ft = rec.get('freeze_transform') or {}
        if not ft:
            # no freeze_transform: release/amended-receipts/<task>/admission.json stands in when its digest is the one
            # pinned by release/freeze-2026-10-21/freeze-manifest.json
            frozen = RELEASE / 'amended-receipts' / case.name / 'admission.json'
            pinned = json.loads((RELEASE / 'freeze-2026-10-21/freeze-manifest.json').read_text())['files']
            if frozen.is_file() and sha(frozen) == pinned.get(f'experiment/benchmark/scamworld/cases/{case.name}/admission.json'):
                rec = json.loads(frozen.read_text()); ft = rec.get('freeze_transform') or {}
        digest = sha(p)
        keys = {old_relative(p.relative_to(case).as_posix())}
        src = image.get('src')
        if isinstance(src, str) and src.startswith('/') and served_file(case / 'site', src) == p:
            keys.add('public/' + src.lstrip('/'))   # construction assets are served under neutral names (rename_path)
        keys |= {k for k, v in (rec.get('case_hashes') or {}).items() if k.startswith('fe-src/') and v == digest}
        # the private original is not shipped when a served file has the same bytes; the receipt binds it by that hash
        m = image.get('asset_manifest') or {}
        if not ft or digest not in {rec.get('case_hashes', {}).get(k) for k in keys} or image.get('sha256') != digest:
            return False
        if m.get('kind') == 'captured_local_reuse' and m.get('source_original_sha256') != digest:
            return False
        return any(v == digest and k.startswith(('public/assets/', 'fe-src/assets/')) for k, v in (ft.get('old_manifest') or {}).items())
    except (OSError, ValueError, AttributeError):
        return False


def public_manifest_binds(local_image, image):
    """Public tree: the freeze receipts and donor captures are not shipped. The reuse was checked against them before
    export; the public manifest (release/path-map.json) pins the exported bytes, so accept an image whose bytes are the
    declared ones and the pinned ones."""
    try:
        doc = json.loads((RELEASE / 'path-map.json').read_text())
        if doc.get('schema') != 'scamworld.public_manifest.v1':
            return False
        p = Path(local_image).resolve()
        rel = 'tasks/' + p.relative_to(CAPTURE_CASES.resolve()).as_posix()
        digest = sha(p)
        return image.get('sha256') == digest and any(r.get('new') == rel and r.get('new_sha256') == digest for r in doc['rows'])
    except (OSError, ValueError, KeyError):
        return False


def validate_reuse(image, local_image):
    m = image.get('asset_manifest', {})
    if m.get('kind') in ('self_claimed_capture_local_reuse', 'captured_local_reuse') and public_manifest_binds(local_image, image):
        require(not image.get('generation_manifest'), 'captured reuse must not impersonate generated provenance')
        return dict(m)
    if m.get('kind') in ('self_claimed_capture_local_reuse', 'captured_local_reuse') and frozen_receipt_binds(local_image, image):
        require(not image.get('generation_manifest'), 'captured reuse must not impersonate generated provenance')
        return dict(m)
    # kind self_claimed_capture_local_reuse is accepted only by the two checks above; the donor checks follow.
    if m.get('kind') == 'self_claimed_capture_local_reuse':
        raise ValueError('an image reused from the task\'s own capture is accepted only when release/path-map.json or the '
                         'task\'s admission record pins its bytes')
    require(not image.get('generation_manifest'), 'captured reuse must not impersonate generated provenance')
    require(m.get('kind') == 'captured_local_reuse' and m.get('scope') == SCOPE,
            'captured image requires explicit reuse origin and design-only scope')
    cid = m.get('source_case_id', '')
    require(re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._-]+', cid) and 'fixture' not in cid.lower(),
            'invalid captured source case')
    case = CAPTURE_CASES / cid
    require(not case.is_symlink() and case.resolve().parent == CAPTURE_CASES.resolve(), 'captured case escaped approved root')
    require(sha(FREEZE_MANIFEST) == FREEZE_SHA256, 'frozen source manifest changed')
    frozen = json.loads(FREEZE_MANIFEST.read_text())
    require(cid in {r['case_id'] for r in frozen['cases']}, 'captured reuse source must belong to frozen v1')
    # the manifest keys each file by its path in the earlier task layout (the prefix below), not by its path under tasks/
    prefix = 'experiment/benchmark/scamworld/cases/' + cid + '/'
    restoration = case / 'source/restoration.json'
    require(restoration.is_file() and not restoration.is_symlink(), 'captured source restoration missing')
    require(sha(restoration) == m.get('source_restoration_sha256') == frozen['files'].get(prefix + 'restoration.json'),
            'captured source restoration changed')
    require(type(m.get('source_part')) is int and m['source_part'] >= 0, 'captured source part must be an integer')
    rows = [r for r in json.loads(restoration.read_text())['parts'] if r.get('part') == m.get('source_part')]
    require(len(rows) == 1, 'captured source part ambiguous or missing')
    part = rows[0]
    require(part.get('mime') in MIMES, 'captured reuse must be a decodable raster MIME part')
    rel = part.get('original_path', '')
    require(isinstance(rel, str) and rel.startswith('private/parts/'), 'source must be an original captured part')
    source = case / layout_new(rel)
    require(source.resolve().is_relative_to((case / 'source/parts').resolve()) and not source.is_symlink(),
            'captured source escaped original parts')
    require(source.is_file(), 'captured original part missing')
    require(m.get('source_original_path') == rel and m.get('source_location') == part.get('source_location'),
            'captured part location binding differs')
    require(sha(source) == part.get('original_sha256') == m.get('source_original_sha256') == frozen['files'].get(prefix + rel)
            == image.get('sha256') == sha(local_image), 'captured reuse is not byte-identical')
    return dict(m)
