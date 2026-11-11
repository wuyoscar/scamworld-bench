"""Text matching of clue_texts / evidence_texts against an observation, and of an anchor's text_contains.

Offline (score.py; clue_match / StepText.match), in this order, the first that contains the text:
  raw              the substring of json.dumps(observation), as the first r8 episodes were scored;
  leaf_normalised  one string of the observation, both sides NFKC with all whitespace removed;
  joined_adjacent  up to JOIN_LEAVES consecutive entries of one ordered text list (JOIN_LISTS, document order), joined and
                   normalised the same way. "1.5%" followed by <span>"Daily For 7 Days"</span> are adjacent entries of the
                   agent's own input and the page renders them as one phrase. Never across lists, observations or
                   non-adjacent entries. (Joining with "" or " " is the same once whitespace is removed.)
Runtime (env/environment.py): an anchor's text_contains matches 'raw', else 'whitespace_insensitive' (same normalisation).
recorded_evaluator() (rescore.py) sets NORMALISED = False: the raw match only, as recorded.
"""
import json
import unicodedata

MATCH_KINDS = ('raw', 'leaf_normalised', 'joined_adjacent')
JOIN_LISTS = ('public_accessibility_text', 'visible_text_regions')
JOIN_LEAVES = 4
NORMALISED = True


def squash(text):
    """NFKC, then every whitespace character removed."""
    return ''.join(unicodedata.normalize('NFKC', text).split())


def text_contains_match(text, needle):
    """'raw' or 'whitespace_insensitive' when text contains the anchor's text_contains, else None."""
    if needle in text:
        return 'raw'
    return 'whitespace_insensitive' if squash(needle) and squash(needle) in squash(text) else None


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


def _entry_text(entry):
    if isinstance(entry, dict):
        entry = entry.get('text')
    return entry if isinstance(entry, str) else ''


class StepText:
    """One step's observation as the matcher reads it: the raw serialisation now, the normalised forms on first need."""

    def __init__(self, step):
        self.observation = step.get('observation', {})
        self.raw = json.dumps(self.observation, ensure_ascii=False)
        self._leaves = self._windows = None

    def _normalised(self):
        if self._leaves is None:
            observation = self.observation if isinstance(self.observation, dict) else {}
            self._leaves = [s for s in map(squash, _strings(observation)) if s]
            self._windows = []
            for name in JOIN_LISTS:
                entries = [squash(_entry_text(e)) for e in observation.get(name) or []]
                for i in range(len(entries) - 1):
                    for k in range(2, JOIN_LEAVES + 1):
                        if i + k <= len(entries):
                            self._windows.append(''.join(entries[i:i + k]))
        return self._leaves, self._windows

    def match(self, needle):
        """The first of MATCH_KINDS whose text contains needle, else None."""
        if needle in self.raw:
            return 'raw'
        n = squash(needle) if NORMALISED else ''
        if not n:
            return None
        leaves, windows = self._normalised()
        if any(n in leaf for leaf in leaves):
            return 'leaf_normalised'
        if any(n in window for window in windows):
            return 'joined_adjacent'
        return None


def clue_match(needle, step):
    """How the observation of `step` (a trace step) contains `needle`: 'raw' | 'leaf_normalised' | 'joined_adjacent' | None.
    The function score.py uses (through StepText); clue scans can call it directly."""
    return StepText(step).match(needle)


def first_hit(texts, steps, needles):
    """(step_id, kind) of the first step whose observation contains any of needles; kind is the best kind at that step
    (MATCH_KINDS order). (None, None) when none does."""
    for step, text in zip(steps, texts):
        kinds = {text.match(n) for n in needles}
        kind = next((k for k in MATCH_KINDS if k in kinds), None)
        if kind:
            return step.get('step_id'), kind
    return None, None


def best_hit(texts, needle):
    """The best kind with which any step contains needle (MATCH_KINDS order), else None."""
    best = None
    for text in texts:
        kind = text.match(needle)
        if kind == 'raw':
            return kind
        if kind and (best is None or MATCH_KINDS.index(kind) < MATCH_KINDS.index(best)):
            best = kind
    return best
