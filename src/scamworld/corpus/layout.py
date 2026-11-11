"""Task folder layout (docs/task-format.md) and its mapping to the older case layout the tasks were built in.

    tasks/<task>/task.json        public task contract (instruction, start page, answer format)
    tasks/<task>/site/            the website: the only folder the local server serves to the agent
    tasks/<task>/scoring/         hidden scoring inputs: spec.json (rubric, paths, answers), evaluation.json
    tasks/<task>/source/          the captured original page and its provenance (read by the runtime for the logical URL)
    tasks/<task>/records/         construction and admission records (not read at run time)

Old case layout -> task layout: public/ -> site/, build/spec.json -> scoring/spec.json, evaluation.json ->
scoring/evaluation.json, private/ -> source/, provenance.json and restoration.json -> source/, build/, audit/, fe-src/ and
other top-level JSON -> records/. score_case.py and verify_case.py (identical in every case; LEGACY_SCRIPTS) are not
copied into the task folder. Bytes are unchanged except the served site files (scamworld.corpus.neutral_names).
"""
LEGACY_SCRIPTS = ('score_case.py', 'verify_case.py')
SOURCE_TOP = ('provenance.json', 'restoration.json')
RECORD_DIRS = ('build', 'audit', 'fe-src')


def new_relative(old):
    """Path inside an old case folder -> path inside the task folder."""
    p = old.split('/')
    if p[0] == 'public':
        return 'site/' + '/'.join(p[1:])
    if old == 'build/spec.json':
        return 'scoring/spec.json'
    if old == 'evaluation.json':
        return 'scoring/evaluation.json'
    if old == 'task.json':
        return 'task.json'
    if p[0] == 'private':
        return 'source/' + '/'.join(p[1:])
    if old in SOURCE_TOP:
        return 'source/' + old
    if p[0] in RECORD_DIRS or (len(p) == 1 and old.endswith('.json')):
        return 'records/' + old
    raise ValueError('unmapped task file: ' + old)


def old_relative(new):
    """Inverse of new_relative (a site file renamed by neutral_names.rename_path keeps its served name)."""
    p = new.split('/')
    if p[0] == 'site':
        return 'public/' + '/'.join(p[1:])
    if new == 'scoring/spec.json':
        return 'build/spec.json'
    if new == 'scoring/evaluation.json':
        return 'evaluation.json'
    if new == 'task.json':
        return new
    if p[0] == 'source':
        return p[1] if len(p) == 2 and p[1] in SOURCE_TOP else 'private/' + '/'.join(p[1:])
    if p[0] == 'records':
        return '/'.join(p[1:])
    raise ValueError('not a task file: ' + new)
