"""Dead-link layer 1: no same-origin dead link survives in a served page.

Runs on the original bytes of every public/**/*.html (site/ of the task folder holds the result), before the neutral names
(step 0 of the site transform), so it reads the names used in the task files (data-sw-do, .sw-view, /__uncaptured__/...),
not the names served to the page:
  links  <a>/<area> whose href resolves to the site's own origin (or is relative) and that the local static server cannot
         serve get href="#" (a[href] styling stays, a click is a no-op, not a 404); text, classes and every other attribute
         stay. A link whose visible text promises sign-in, registration, an account or a purchase step (CTA_TEXT) loses its
         href instead: a dead "#" there makes the agent click it again and again.
  forms  <form> whose submission the runtime cannot serve (non-GET to the own origin, or GET to a path that is no file)
         get onsubmit="return false" before the closing '>' of the start tag.
Never touched: data-sw-do elements and their descendants, anything inside .sw-view, the excluded elements (selectors of
the contract reach them), other hosts, mailto:, tel:, javascript:, fragments. apply_case refuses a page where a selector
of evaluation.json, flow.js or spec.json (`selector`, `trigger`) matches a changed element, so new contract selectors
cannot be cut silently. "Served" is what the runtime serves: a file of public/ (query and fragment dropped; a directory
with index.html), or a navigation route of the source transport. Edits are positional on the source text; every other
byte is kept.

Each edit is recorded in records/a6e-dead-links.json as [offset in the page before the rule, removed text, inserted
text], so the original bytes can be restored exactly after neutral_names.invert (restore_file).

A click on "#" gives the agent no feedback, so it clicks again. A link to a page of the site's own host that the capture
never had (/__uncaptured__/<id>; a list of the original hrefs of each case, `hrefs`) keeps that page's original path instead
(`relative_href`: path?query#fragment), CTA links included, and the local server answers it with its plain 404 page
(env/runtime.py), as the live server of a vanished page would. When that path is one the server does serve (the site root
with a query, /?page_id=12), the path?query is listed under "unavailable" in the sidecar and the runtime answers it with the
same 404. Links to other hosts, non-http links, ids the list cannot resolve, hrefs that would collide with a served name of
corpus/neutral_names.py and hrefs with a placeholder-like digit run (PLACEHOLDER) keep the rule above.
"""
import html
import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urljoin, urlparse, urlsplit

SIDECAR_NAME = 'a6e-dead-links.json'
RULE = 'a6e-dead-links'
SKIP = re.compile(r'(?i)^\s*(#|javascript:|mailto:|tel:|sms:|data:|blob:)')
HREF = re.compile(r'''\s+href\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)''', re.I)
ONSUBMIT = ' onsubmit="return false"'
NOOP_HREF = 'href="#"'
# visible text of an anchor that promises sign-in, registration, account navigation or a purchase step
CTA_TEXT = re.compile(r"\b(log ?in|log ?on|sign ?in|sign ?up|register|registration|my account|create account|open (an |a new )?account|"
                      r"join( now| us| free)?|member login)\b|登录|登入|注册|註冊|登錄|會員|ورود|ثبت ?نام|đăng nhập|đăng ký|tài khoản|"
                      r"\bmasuk\b|\bdaftar\b|entrar|registr|connexion|s'inscrire|inscription|anmelden|registrieren|accedi|"
                      r"iniciar sesi|crear cuenta|войти|вход|авторизац|регистрац|ログイン|新規登録|로그인|회원가입|giriş|kayıt|"
                      r"log på|login|tilmeld"
                      r"|\b(deposit|invest( now)?|buy( now)?|get started|start now|start investing|order now|subscribe|claim|apply( now| online)?|donate|withdraw|purchase|checkout|book now|pay now|add to cart|get money|make deposit)\b", re.I)
SELECTOR = re.compile(r'"(?:selector|trigger)"\s*:\s*"((?:\\.|[^"\\])*)"')
UNCAPTURED = re.compile(r'^/__uncaptured__/([0-9a-f]{20})$')
# six or more equal digits in a row, which read as a placeholder value on the page (e.g. ok-invest-02's zero address)
PLACEHOLDER = re.compile(r'(\d)\1{5,}')


def request_key(path):
    """The server's key of a request path or a site-relative href: unquoted path, plus '?' and the unquoted query when there is
    one (the fragment never reaches the server). The runtime compares a request's raw path with `unavailable` by this key."""
    u = urlsplit(path)
    return unquote(u.path or '/') + ('?' + unquote(u.query) if u.query else '')


def site_hrefs(doc, cid):
    """{id: relative_href} of the same-site links of one case in the list of original hrefs, {} when the case has none."""
    links = ((doc or {}).get('cases', {}).get(cid) or {}).get('links') or {}
    return {i: l['relative_href'] for i, l in links.items() if l.get('class') == 'same_site' and l.get('relative_href', '').startswith('/')}


def _collides(attr):
    """True when the inserted attribute holds a served name of the site transform (it would not invert, e.g. a path /link/...)."""
    from scamworld.corpus import neutral_names as N
    data = attr.encode('utf-8')
    return any(t.inv.search(data) for t in N._TOKENS)


def shown_text(el):
    """The anchor's visible text as the rule reads it."""
    return ' '.join(el.get_text(' ').split()) or el.get('aria-label') or el.get('title') or ''


def promises_step(el):
    t = shown_text(el)
    return bool(t) and len(t) <= 60 and bool(CTA_TEXT.search(t))


def contract_selectors(*texts):
    """CSS selectors named by `selector` / `trigger` keys of evaluation.json, flow.js and spec.json texts."""
    return sorted({json.loads('"' + m.group(1) + '"') for t in texts if t for m in SELECTOR.finditer(t)})


def _served(files, path):
    p = unquote(path).lstrip('/')
    if p.endswith('/') or not p:
        return (p + 'index.html') in files
    return p in files or (p + '/index.html') in files


def origin_of(provenance, evaluation):
    from scamworld.env.transport import resolve_source_transport
    logical, transport = resolve_source_transport(provenance, evaluation)
    o = urlparse(logical)
    routes = {r['url'] for r in (transport or {}).get('navigation_routes', [])}
    return f'{o.scheme}://{o.netloc.lower()}', (o.hostname or '').lower(), routes


def _dead(url, base, files, origin, host, routes):
    try:
        u = urlparse(urljoin(base, url))
    except ValueError:
        return False
    if u.scheme not in ('http', 'https') or u._replace(fragment='').geturl() in routes:
        return False
    if f'{u.scheme}://{u.netloc.lower()}' != origin and (u.hostname or '').lower() != host:
        return False
    return not _served(files, u.path or '/')


def _tag_end(text, start):
    q, prev = None, ''
    for i in range(start, len(text)):
        c = text[i]
        if q:
            if c == q:
                q = None
        elif c in '"\'' and prev == '=':
            q = c
        elif c == '>':
            return i
        if not c.isspace():
            prev = c
    raise ValueError('unterminated tag')


def page_edits(text, files, rel, origin, host, routes, excluded, selectors=(), hrefs=None, unavailable=None):
    """[(start, end, replacement)] on one page's text (positions before the rule). hrefs: {id: relative_href};
    unavailable: a set that collects the request keys of kept hrefs whose path the server serves."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(text, 'html.parser')
    base = origin + '/' + rel
    b = soup.find('base', href=True)
    if b:
        base = urljoin(base, b['href'])
    line_starts = [0] + [m.end() for m in re.finditer('\n', text)]
    offset = lambda el: line_starts[el.sourceline - 1] + el.sourcepos
    edits, touched = [], []

    def protected(el):
        if el.has_attr('data-sw-do') or el.find_parent(attrs={'data-sw-do': True}) or el.find_parent(class_='sw-view'):
            return True
        return (el.name, el.get('href') if el.name != 'form' else el.get('action'), el.get('id')) in excluded

    for el in soup.find_all(['a', 'area'], href=True):
        h = el['href']
        if SKIP.match(h) or not h.strip() or protected(el):
            continue
        if _dead(h.strip(), base, files, origin, host, routes):
            s = offset(el); e = _tag_end(text, s)
            m = HREF.search(text, s, e)
            if not m:
                raise ValueError(f'{rel}: href not found in source tag at {s}')
            lead = m.group(0)[:len(m.group(0)) - len(m.group(0).lstrip())]
            u = UNCAPTURED.match(h.strip())
            kept = (hrefs or {}).get(u.group(1)) if u else None
            attr = lead + 'href="' + html.escape(kept, quote=True) + '"' if kept else None
            if attr and not _collides(attr) and not PLACEHOLDER.search(kept):   # the page's original path; the server answers 404
                edits.append((m.start(), m.end(), attr))
                if urlsplit(kept).query and _served(files, urlsplit(kept).path or '/') and unavailable is not None:
                    unavailable.add(request_key(kept))
            else:
                edits.append((m.start(), m.end(), '' if promises_step(el) else lead + NOOP_HREF))
            touched.append(el)
    for f in soup.find_all('form'):
        if protected(f) or f.has_attr('onsubmit'):
            continue
        method = (f.get('method') or 'get').strip().lower()
        action = (f.get('action') or '').strip()
        if method == 'get' and (not action or action.startswith('#') or not _dead(action, base, files, origin, host, routes)):
            continue
        if method != 'get' and action and not SKIP.match(action):
            try:
                u = urlparse(urljoin(base, action))
                if f'{u.scheme}://{u.netloc.lower()}' != origin and (u.hostname or '').lower() != host:
                    continue
            except ValueError:
                continue
        s = offset(f); e = _tag_end(text, s)
        at = e - 1 if text[e - 1] == '/' else e
        edits.append((at, at, ONSUBMIT))
        touched.append(f)
    if touched and selectors:
        ids = {id(el) for el in touched}
        for sel in selectors:
            try:
                hit = soup.select(sel)
            except Exception:   # a selector soupsieve cannot parse reaches nothing it could check; the browser decides
                continue
            if any(id(el) in ids for el in hit):
                raise ValueError(f'{rel}: contract selector {sel!r} matches an element the rule would change; add it to the exclusions')
    edits.sort()
    if any(a[1] > b[0] for a, b in zip(edits, edits[1:])):
        raise ValueError(f'{rel}: overlapping edits')
    return edits


def apply_edits(text, edits):
    out, at = [], 0
    for s, e, rep in edits:
        out.append(text[at:s]); out.append(rep); at = e
    out.append(text[at:])
    return ''.join(out)


def apply_case(cid, files, provenance, evaluation, exclusions=None, selectors=(), hrefs=None):
    """files: {public-relative path: original bytes} of one case -> ({path: new bytes} of the changed pages, sidecar bytes
    or None, {path: (links changed, forms stopped)}). selectors: contract_selectors() of the case; hrefs: site_hrefs()."""
    origin, host, routes = origin_of(provenance, evaluation)
    excluded = {(x['tag'], x['value'], x.get('id')) for x in (exclusions or {}).get(cid, [])}
    changed, doc, counts, unavailable = {}, {}, {}, set()
    for rel in sorted(files):
        if PurePosixPath(rel).suffix != '.html':   # public/**/*.html, as the rule
            continue
        text = files[rel].decode('utf-8')
        edits = page_edits(text, files, rel, origin, host, routes, excluded, selectors, hrefs, unavailable)
        if not edits:
            continue
        new = apply_edits(text, edits).encode('utf-8')
        if restore(new, [[s, text[s:e], rep] for s, e, rep in edits]) != files[rel]:
            raise ValueError(f'{cid}/{rel}: A6e edit does not invert')
        changed[rel] = new
        doc[rel] = [[s, text[s:e], rep] for s, e, rep in edits]
        counts[rel] = (sum(1 for *_, r in edits if r != ONSUBMIT), sum(1 for *_, r in edits if r == ONSUBMIT))
    if not doc:
        return {}, None, {}
    side = {'schema': 1, 'rule': 'A6e layer 1 (the internal notes)', 'files': doc}
    if unavailable:   # request keys the runtime answers with 404 although the path is served
        side['unavailable'] = sorted(unavailable)
    return changed, dumps_sidecar(side), counts


def dumps_sidecar(doc):
    return (json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + '\n').encode('utf-8')


def restore(data, edits):
    """Page bytes before the rule from the bytes after it and its recorded edits [[offset before, removed, inserted]]."""
    text = data.decode('utf-8')
    out, at, shift = [], 0, 0
    for start, removed, inserted in sorted(edits, key=lambda x: x[0]):
        p = start + shift
        if text[p:p + len(inserted)] != inserted:
            raise ValueError(f'A6e sidecar does not fit the page at {start}')
        out.append(text[at:p]); out.append(removed); at = p + len(inserted)
        shift += len(inserted) - len(removed)
    out.append(text[at:])
    return ''.join(out).encode('utf-8')


def sidecar(task_dir):
    p = task_dir / 'records' / SIDECAR_NAME
    return json.loads(p.read_text()) if p.is_file() else None


def unavailable(task_dir):
    """Request keys (request_key) the local server of this task answers with 404 although their path is served."""
    return frozenset((sidecar(Path(task_dir)) or {}).get('unavailable') or ())


def restore_file(task_dir, public_rel, data, doc=None):
    """Bytes of one page (public/<public_rel>) before the rule; unchanged when the task has no edit for it."""
    doc = sidecar(task_dir) if doc is None else doc
    edits = ((doc or {}).get('files') or {}).get(public_rel)
    return restore(data, edits) if edits else data
