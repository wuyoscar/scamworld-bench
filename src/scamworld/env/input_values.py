"""Date and time inputs: the text an agent types is put into the form the browser's input control takes.

A native `<input type=date|month|time|datetime-local>` only accepts one machine form (YYYY-MM-DD, YYYY-MM, HH:MM,
YYYY-MM-DDTHH:MM) whatever it displays to the person, and Playwright's fill() raises "Malformed value" for any other text. A
person types the date the way the control shows it; the agent reads the displayed form (dd.mm.yyyy, mm/dd/yyyy, ...) off the
page and types that. normalize_input_value() turns a typed text that has one unambiguous reading into the control's form
before it is entered (dd.mm.yyyy with dots is always day first); an ambiguous one (slashes or dashes, day and month both 12
or less, no year first) is left as typed, fails, and
malformed_value_message() tells the agent which form the field takes.

Pure functions; the wiring is in env/browsergym_adapter.py (rewrite_fill_action) and env/action_errors.py.
"""
import ast
import datetime
import re

SPECIAL_TYPES = ('date', 'month', 'time', 'datetime-local')

FORMS = {'date': 'a date in YYYY-MM-DD form', 'month': 'a month in YYYY-MM form', 'time': 'a time in HH:MM form',
         'datetime-local': 'a date and time in YYYY-MM-DDTHH:MM form', 'week': 'a week in YYYY-Www form'}

_DAY = r'(\d{1,2})'
_YEAR = r'(\d{4})'
_SEP = r'([./-])'
# 18.07.2026, 18/07/2026, 07/18/2026, 2026/07/18, 2026-7-18, 2026.07.18 (separators of one kind)
_DMY = re.compile(rf'^{_DAY}([./-]){_DAY}\2{_YEAR}$')
_YMD = re.compile(rf'^{_YEAR}([./-]){_DAY}\2{_DAY}$')
_YM = re.compile(rf'^{_YEAR}[./-](\d{{1,2}})$')
_MY = re.compile(rf'^(\d{{1,2}})[./-]{_YEAR}$')
_TIME = re.compile(r'^(\d{1,2})[:.](\d{2})(?::(\d{2})(?:\.\d+)?)?\s*([ap]\.?m\.?)?$', re.I)
_DATETIME = re.compile(r'^(.+?)(?:T|\s+)(\d{1,2}[:.]\d{2}(?::\d{2}(?:\.\d+)?)?\s*(?:[ap]\.?m\.?)?)\s*(?:Z|[+-]\d{2}:?\d{2})?$', re.I)


def _valid_date(y, m, d):
    try:
        datetime.date(y, m, d)
    except ValueError:
        return False
    return True


def _date(text):
    """ISO date of a typed date, or None when it is not a date or has two readings."""
    text = text.strip()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
        return text if _valid_date(*map(int, text.split('-'))) else None
    m = _YMD.match(text)
    if m:   # the year first is one reading
        y, a, b = int(m.group(1)), int(m.group(3)), int(m.group(4))
        return f'{y:04d}-{a:02d}-{b:02d}' if _valid_date(y, a, b) else None
    m = _DMY.match(text)
    if not m:
        return None
    a, b, y = int(m.group(1)), int(m.group(3)), int(m.group(4))
    if m.group(2) == '.' and a <= 31 and b <= 12:   # dd.mm.yyyy: wherever dots are used the day comes first
        day, month = a, b
    elif a > 12 and b <= 12:
        day, month = a, b
    elif b > 12 and a <= 12:
        day, month = b, a
    else:
        return None   # both 12 or less (two readings) or neither a month
    return f'{y:04d}-{month:02d}-{day:02d}' if _valid_date(y, month, day) else None


def _month(text):
    text = text.strip()
    if re.fullmatch(r'\d{4}-\d{2}', text):
        return text if 1 <= int(text[5:]) <= 12 else None
    m = _YM.match(text) or None
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
    else:
        m = _MY.match(text)
        if not m:
            return None
        mo, y = int(m.group(1)), int(m.group(2))
    return f'{y:04d}-{mo:02d}' if 1 <= mo <= 12 else None


def _time(text):
    """HH:MM (HH:MM:SS stays as typed) of a typed time; 12-hour times with am / pm are converted."""
    text = text.strip()
    m = _TIME.match(text)
    if not m:
        return None
    h, mi, sec, ampm = int(m.group(1)), int(m.group(2)), m.group(3), (m.group(4) or '').lower().replace('.', '')
    if ampm:
        if not 1 <= h <= 12:
            return None
        h = h % 12 + (12 if ampm == 'pm' else 0)
    if h > 23 or mi > 59 or (sec is not None and int(sec) > 59):
        return None
    return f'{h:02d}:{mi:02d}' + (f':{sec}' if sec is not None and not ampm else '')


def _datetime(text):
    m = _DATETIME.match(text.strip())
    if not m:
        return None
    day, clock = _date(m.group(1)), _time(m.group(2))
    return f'{day}T{clock}' if day and clock else None


def normalize_input_value(input_type, value):
    """The text to enter into an input of `input_type`: the control's own form when `value` has one unambiguous reading, else
    `value` unchanged (a value already in the control's form is never altered)."""
    if not isinstance(value, str) or input_type not in SPECIAL_TYPES:
        return value
    out = {'date': _date, 'month': _month, 'time': _time, 'datetime-local': _datetime}[input_type](value)
    return value if out is None else out


def input_type_of(raw):
    """The type of the input a failed fill resolved to, from Playwright's call log (`<input ... type="date" ...>`)."""
    for tag in re.findall(r'<input\b[^>]*>', raw or ''):
        m = re.search(r'\btype="([a-z-]+)"', tag)
        if m and m.group(1) in FORMS:
            return m.group(1)
    return None


def malformed_value_message(raw):
    """The sentence for a fill that Playwright rejected as a malformed value ("Malformed value"), naming the form the field takes."""
    kind = input_type_of(raw)
    if kind is None:
        return 'The text entry could not be performed: this field does not accept that value.'
    return f'The text entry could not be performed: this field only accepts {FORMS[kind]}.'


def rewrite_fill_action(text, input_type_of_bid):
    """(new action text, [(bid, typed, entered)]) for a BrowserGym action string whose fill() calls type text into date / month / time
    / datetime-local inputs. input_type_of_bid(bid) -> the input's type or None (bid not found, not an input). The text is
    returned unchanged when nothing has to be rewritten; every statement must be a call with literal arguments (the adapter has
    already checked this)."""
    tree = ast.parse(text)
    changes = []
    for node in tree.body:
        call = getattr(node, 'value', None)
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == 'fill' and len(call.args) == 2 and not call.keywords):
            continue
        bid, typed = (ast.literal_eval(a) for a in call.args)
        if not isinstance(bid, str) or not isinstance(typed, str):
            continue
        entered = normalize_input_value(input_type_of_bid(bid), typed)
        if entered != typed:
            call.args[1] = ast.Constant(entered)
            changes.append((bid, typed, entered))
    return (ast.unparse(tree), changes) if changes else (text, [])
