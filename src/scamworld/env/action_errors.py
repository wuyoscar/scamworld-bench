"""What the agent is told when a browser action raises.

Playwright raises on a click whose navigation is slow, whose page replaces its document mid-call or whose element
detaches after the event fired, although the click was dispatched and the page changed. The raw text (call log,
locator, timeout) made agents think the click had failed. classify_action_error() separates those from real
failures: a dispatched or visibly effective action reports nothing; a real failure gets one short neutral
sentence (never Playwright text, paths or benchmark names). The raw text is kept in the trace (`raw_action_error`).
"""
import re

from .input_values import malformed_value_message

UNREACHABLE = "This site can't be reached."   # an off-site address (goto) or, under a11, an off-site link (environment.FormalBrowserTask)
SETTLE_SECONDS = 10   # total wait for the page to finish loading after an action, before it is observed

# Evidence that the pointer/select action itself ran (Playwright 1.44 call-log markers).
DISPATCHED = re.compile(r'\b(?:click|dblclick|hover|tap) action done|selected specified option')
# Retry-loop states of the actionability checks: the action never reached the element. (pattern, reason)
BLOCKED = tuple((re.compile(p), why) for p, why in (
    ('intercepts pointer events', 'the element is covered by another element'),
    ('element is outside of the viewport', 'the element is outside the visible part of the page'),
    ('element is not visible', 'the element is not visible'),
    ('element is not stable', 'the element is still moving'),
    ('element is not enabled', 'the element is disabled'),
    ('element is not editable', 'the element cannot be edited'),
    ('is not an <input>', 'the element cannot be edited'),   # a11 lets fill reach any element the page shows
    ('Cannot type text into input', 'the element cannot be edited'),
    ('Element is not a <select> element', 'the element is not a list of options'),
    ('did not find some options', 'the option was not found')))
PERFORMING = re.compile(r'performing .+? action')
LOCATOR_TIMEOUT = re.compile(r'TimeoutError: (?:Locator|ElementHandle)\.')
VERBS = {'click': 'click', 'dblclick': 'click', 'hover': 'hover', 'fill': 'text entry', 'clear': 'text entry', 'type': 'text entry',
         'press': 'key press', 'select_option': 'selection', 'check': 'selection', 'uncheck': 'selection'}
INVALID = ('ValueError', 'SyntaxError', 'NameError', 'TypeError', 'KeyError', 'IndexError', 'AttributeError')

# Page signature taken around an action; changing any CHANGE_KEYS entry, or a new dom_action, shows the action took effect.
SIGNATURE_JS = """() => {
  const dump = read => { try { return JSON.stringify(Object.entries(read())); } catch (e) { return null; } };
  const events = window.__pagekitRuntimeEvents || [];
  return {doc: {url: location.href, time_origin: performance.timeOrigin},
          state_id: document.body ? document.body.dataset.stateId || null : null,
          values: Array.from(document.querySelectorAll('input,select,textarea')).map(e => e.type === 'checkbox' || e.type === 'radio' ? e.checked : e.value),
          storage: [dump(() => localStorage), dump(() => sessionStorage)],
          dispatches: events.filter(e => e.type === 'dom_action' || e.type === 'form_submit_attempt').length};
}"""
CHANGE_KEYS = ('state_id', 'values', 'storage', 'pages')


def _last(pattern, text):
    """Start offset of the last match, or -1."""
    found = -1
    for m in pattern.finditer(text):
        found = m.start()
    return found


def action_signals(before, after):
    """Signals for classify_action_error from two page signatures (None: the page could not be read)."""
    if before is None:
        return {}
    if after is None:   # page closed or navigating away: the action did something
        return {'changed': True}
    same = before['doc'] == after['doc']
    return {'dispatched': same and after['dispatches'] > before['dispatches'],
            'changed': not same or any(before[k] != after[k] for k in CHANGE_KEYS)}


def navigation_pending(raw):
    """The click ran and Playwright was still waiting for the navigation it scheduled when its timeout hit."""
    return 'waiting for scheduled navigations to finish' in raw and 'navigations have finished' not in raw and 'navigated to' not in raw


def classify_action_error(raw, *, dispatched=False, changed=False):
    """(message for the agent or None, raw). None: not an error from the agent's point of view.

    dispatched: a DOM event of this action reached the page. changed: URL, document, state, form values or storage
    differ from before the action. Definitive failures (element missing, covered, hidden, invalid action) are
    reported whatever else changed on the page; an unknown outcome (hung event handler, navigation or document
    replacement in flight, detached element) is reported only if nothing changed."""
    raw = raw or ''
    if not raw.strip():
        return None, raw
    if dispatched or DISPATCHED.search(raw):
        return None, raw
    verb = VERBS.get((re.search(r'(?:Locator|ElementHandle)\.(\w+)', raw) or [None, ''])[1], 'action')
    if 'Could not find element with bid' in raw:
        return 'No element with that ID on this page.', raw   # the same words as interface_v11.NO_ELEMENT
    if 'Only the owned loopback origin' in raw:
        return UNREACHABLE, raw
    if 'External website outside the offsite allowlist' in raw:   # offsite.BLOCKED_ERROR (experiment option offsite)
        return 'This website cannot be opened.', raw
    if 'Only one tab is open' in raw:
        return 'The only open tab cannot be closed.', raw
    if 'No tab with that index' in raw:   # tab_focus out of range: browsergym_adapter's ValueError, else 'The action is not valid.'
        return 'There is no tab with that index.', raw
    if 'Unknown key:' in raw:   # Keyboard.press of a word or an address; would otherwise read 'the page did not respond in time'
        return 'The key press could not be performed: that is not a key name.', raw
    if 'Malformed value' in raw:   # Playwright fill() of text a date / month / time input cannot take (else 'did not respond in time')
        return malformed_value_message(raw), raw
    kind = (re.match(r'(\w*Error):', raw) or [None, 'Error'])[1]
    if kind not in ('TimeoutError', 'Error'):
        return ('The action is not valid.' if kind in INVALID else 'The action could not be performed.'), raw
    performed = _last(PERFORMING, raw)
    blocked = max(((_last(p, raw), why) for p, why in BLOCKED), key=lambda hit: hit[0])
    if blocked[0] > performed:
        return f'The {verb} could not be performed: {blocked[1]}.', raw
    if performed < 0 and LOCATOR_TIMEOUT.match(raw):   # never became actionable, so nothing was dispatched
        return f'The {verb} could not be performed: the element did not become available in time.', raw
    return (None, raw) if changed else (f'The {verb} could not be performed: the page did not respond in time.', raw)
