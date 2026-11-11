"""The frozen task set: task folders, the task index (tasks/index.json) and per-task scoring specs.

corpus() and verify() check the task bytes against release/path-map.json (sha256 of every released task file) and
fail loudly, naming the tasks, instead of dropping a task from the corpus.
"""
import hashlib
import json
import os
import time
from pathlib import Path

from scamworld import paths
from scamworld.corpus.ids import legacy_prefix
from scamworld.paths import TASKS

SKIP_NAMES = {'.DS_Store', '.metadata_never_index'}
CHECKED_DIRS = ('site', 'scoring')   # files here (served or scoring) must all be released files


class CorpusError(RuntimeError):
    pass


def task_dir(task):
    return TASKS / task   # module global, read at call time: ablation runs point TASKS at a modified copy


def index():
    return json.loads((TASKS / 'index.json').read_text())


def resolve_task(task):
    """(name, folder) of a task given by id (a folder under TASKS) or by the path of a task folder (one holding task.json),
    e.g. a task made with `scamworld new-task` outside tasks/."""
    folder = Path(task).expanduser()
    if str(task) not in ('', '.') and (folder / 'task.json').is_file() and (folder.is_absolute() or os.sep in str(task) or not (TASKS / str(task)).is_dir()):
        folder = folder.resolve()
        return folder.name, folder
    return str(task), task_dir(str(task))


def spec_at(folder):
    """spec_of for a task folder anywhere (the folder name is the task id)."""
    folder = Path(folder)
    s = json.loads((folder / 'scoring/spec.json').read_text())
    if 'prefix' not in s:
        s['prefix'] = legacy_prefix(folder.name)
    s['case_id'] = folder.name
    return s


def corpus(check_bytes=True):
    """Sorted ids of the tasks of the task index (tasks/index.json) whose `in_corpus` is true. Every row of the released index
    has it: 430 tasks in the full release, the 20 sample tasks in the GitHub tree.

    Raises CorpusError when a listed task's files differ from the release path map (check_bytes=False skips it)."""
    ids = sorted(t['task'] for t in index()['tasks'] if t['in_corpus'])
    if check_bytes:
        require_released(ids)
    return ids


def spec_of(task):
    """Scoring spec of one task, with the derived prefix and the task id (case_id)."""
    s = json.loads((task_dir(task) / 'scoring/spec.json').read_text())
    if 'prefix' not in s:
        s['prefix'] = legacy_prefix(task)
    s['case_id'] = task
    return s


def _released(path_map=None):
    """task -> {path inside the task folder: sha256} from the release path map, for the folder TASKS points at."""
    pm = json.loads((path_map or paths.RELEASE / 'path-map.json').read_text())
    # The literal path first: tasks/ may be a symlink to a copy of the task folders kept elsewhere on disk, so the resolved
    # path leaves SCAMWORLD_HOME although the task folder is the repository's own.
    if TASKS.is_relative_to(paths.REPO):
        prefix = TASKS.relative_to(paths.REPO).as_posix() + '/'
    elif TASKS.resolve().is_relative_to(paths.REPO.resolve()):
        prefix = TASKS.resolve().relative_to(paths.REPO.resolve()).as_posix() + '/'
    else:
        return {}   # a task folder outside the repository (SCAMWORLD_TASKS): nothing in the release path map
    out = {}
    for row in pm['rows']:
        new = row.get('new')
        if row['transform'] != 'retired' and new and new.startswith(prefix):
            task, rel = new[len(prefix):].split('/', 1)
            out.setdefault(task, {})[rel] = row['new_sha256']
    extra = {**(pm.get('a8_files') or {}), **(pm.get('task_tree_files') or {})}   # sidecar files; ablation copies' files
    for new, digest in extra.items():
        if new.startswith(prefix):
            task, rel = new[len(prefix):].split('/', 1)
            out.setdefault(task, {})[rel] = digest
    return out


RACY_NS = 2_000_000_000   # a file changed less than 2 s before it was hashed is hashed again next time (_hasher)


def _hasher():
    """sha256 of a file, memoised in .cache/task-hashes.json so repeated checks are fast. The key includes inode and ctime:
    release tooling can rewrite sidecar files with the source mtime and often the same length, so (size, mtime) alone can
    hold a stale digest. A digest is cached only once the file is RACY_NS old: on a filesystem with coarse timestamps a
    same-size rewrite in the same timestamp tick keeps every field of the key, so an entry taken in that tick could hide it
    (git's "racily clean" entries)."""
    cache_file = paths.CACHE / 'task-hashes.json'
    try:
        cache = json.loads(cache_file.read_text())
    except (OSError, ValueError):
        cache = {}
    if not isinstance(cache, dict):
        cache = {}
    dirty = []

    def digest(p):
        st = p.stat()
        key, stamp = str(p), [st.st_size, st.st_mtime_ns, st.st_ino, st.st_ctime_ns]
        hit = cache.get(key)
        if hit and hit[:-1] == stamp:
            return hit[-1]
        h = hashlib.sha256()
        with open(p, 'rb') as f:
            for block in iter(lambda: f.read(1 << 20), b''):
                h.update(block)
        if time.time_ns() - max(st.st_mtime_ns, st.st_ctime_ns) >= RACY_NS:
            cache[key] = stamp + [h.hexdigest()]; dirty.append(key)
        return h.hexdigest()

    def save():
        if dirty:
            try:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                tmp = cache_file.with_name(f'{cache_file.name}.{os.getpid()}.tmp')
                tmp.write_text(json.dumps(cache)); os.replace(tmp, cache_file)
            except OSError:
                pass
    return digest, save


def verify(tasks, path_map=None):
    """{task: [problem, ...]} for tasks whose files differ from the release path map (empty dict: all match)."""
    released = _released(path_map)
    digest, save = _hasher()
    bad = {}
    for task in tasks:
        files, problems = released.get(task), []
        if not files:
            bad[task] = ['no released files in release/path-map.json']; continue
        folder = task_dir(task)
        for rel, expected in sorted(files.items()):
            p = folder / rel
            if not p.is_file():
                problems.append('missing ' + rel)
            elif digest(p) != expected:
                problems.append('changed ' + rel)
        for sub in CHECKED_DIRS:
            for p in sorted((folder / sub).rglob('*')):
                rel = p.relative_to(folder).as_posix()
                if p.is_file() and p.name not in SKIP_NAMES and rel not in files:
                    problems.append('unreleased ' + rel)
        if problems:
            bad[task] = problems
    save()
    return bad


def require_released(tasks, path_map=None):
    """CorpusError for released tasks whose bytes differ from the path map. A task with rows in the path map, or listed in
    tasks/index.json, is always checked; only a task that is neither (your own task, e.g. made by `scamworld new-task`, or
    listed with "released": false) has nothing to check against and is skipped."""
    listed = {t['task']: t for t in (index()['tasks'] if (TASKS / 'index.json').is_file() else [])}
    rows = _released(path_map)
    tasks = [t for t in tasks if t in rows or (t in listed and listed[t].get('released', True))]
    bad = verify(tasks, path_map)
    if bad:
        detail = '; '.join(f'{t}: {", ".join(p[:3])}{" ..." if len(p) > 3 else ""}' for t, p in sorted(bad.items())[:10])
        raise CorpusError(f'{len(bad)} task(s) differ from release/path-map.json: {", ".join(sorted(bad))}. {detail}')
