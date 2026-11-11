"""Benchmark option url_visibility: `visible` (default; the agent is told the page URL) or `hidden`.

`hidden` removes the page's URL, host and path from everything the harness supplies to the agent; page content (link
targets as the site wrote them, domains the site prints, screenshots of the page) is untouched:
  * the observation's `url` field (and BrowserGym's open-page URL list) is dropped, so older-step summaries carry none;
  * accessibility tree: the document node's `url` property (RootWebArea, also of frames) is dropped, and link / image
    `url` properties that the browser resolved against the site's own origin keep only their path (the absolute form is
    browser output, not page content);
  * action errors: absolute URLs on the site's host (or the local server) are replaced by "the page";
  * the protocol does not offer `goto` and a `goto` action is refused (no action needs a URL; back / forward / tabs stay).
  * the goal: the site's own host in the instruction (bare, www., with a scheme or a path) reads "this website" (some
    instructions name it; scrub_goal, applied once by env.FormalBrowserTask with the task's logical URL). Other names of the
    site (a brand in the text) stay.
Screenshots are viewport captures (CDP Page.captureScreenshot): no address bar or tab strip is drawn.

Selected by SCAMWORLD_URL_VISIBILITY (experiment option url_visibility, e.g. r8-nourl) and recorded in score.json.
"""
import copy
import os
import re
from urllib.parse import urlsplit, urlunsplit

ENV = 'SCAMWORLD_URL_VISIBILITY'
MODES = ('visible', 'hidden')
GOTO_ACTION = '{"action":"goto","url":"http(s) URL"}; '   # entry of interface_v11.PROTOCOL's action list
_URL = re.compile(r'(?i)\b(?:https?|wss?)://[^\s"\'<>()\\\]]+')
_LOOPBACK = {'127.0.0.1', 'localhost', '[::1]', '::1'}


def mode():
    value = os.environ.get(ENV) or 'visible'
    if value not in MODES:
        raise ValueError(f'{ENV} must be one of {", ".join(MODES)}, not {value!r}')
    return value


def hidden():
    return mode() == 'hidden'


def _bare(host):
    host = (host or '').lower()
    return host[4:] if host.startswith('www.') else host


def site_hosts(obs):
    """Hosts that name the site: the current page's host (with and without www.) and the local server."""
    hosts = set(_LOOPBACK)
    for u in [obs.get('url')] + list(obs.get('open_pages_urls') or []):
        if isinstance(u, str) and urlsplit(u).hostname:
            hosts |= {urlsplit(u).hostname.lower(), _bare(urlsplit(u).hostname)}
    return hosts


def _own(url, hosts):
    try:
        host = urlsplit(url).hostname
    except ValueError:
        return False
    return bool(host) and (host.lower() in hosts or _bare(host) in hosts)


def scrub_text(text, hosts):
    """Absolute URLs on the site's hosts in a harness message -> 'the page'."""
    if not isinstance(text, str):
        return text
    return _URL.sub(lambda m: 'the page' if _own(m.group(0), hosts) else m.group(0), text)


def _relative(url):
    p = urlsplit(url)
    return urlunsplit(('', '', p.path or '/', p.query, p.fragment))


def _axtree(axtree, hosts):
    out = copy.deepcopy(axtree)
    for node in out.get('nodes', []):
        props = node.get('properties')
        if not props:
            continue
        role = (node.get('role') or {}).get('value')
        kept = []
        for prop in props:
            value = (prop.get('value') or {}).get('value')
            if prop.get('name') == 'url' and isinstance(value, str):
                if role == 'RootWebArea':
                    continue
                if _own(value, hosts):
                    prop = {**prop, 'value': {**prop['value'], 'value': _relative(value)}}
            kept.append(prop)
        node['properties'] = kept
    return out


def hide_observation(obs, hosts=None):
    """A copy of a BrowserGym observation without the page URL in any harness-supplied field (the input is not changed)."""
    hosts = hosts or site_hosts(obs)
    out = {k: v for k, v in obs.items() if k not in ('url', 'open_pages_urls')}
    if isinstance(obs.get('axtree_object'), dict):
        out['axtree_object'] = _axtree(obs['axtree_object'], hosts)
    if obs.get('last_action_error'):
        out['last_action_error'] = scrub_text(obs['last_action_error'], hosts)
    return out


GOAL_PHRASE = 'this website'


def scrub_goal(text, site_url):
    """The goal with the site's own host (the logical URL's, www. stripped) replaced by GOAL_PHRASE, with any scheme, www. and
    path written around it; capitalised at the start of a sentence. Other hosts (a longer domain ending in it, an e-mail
    address on it) are left as they are."""
    try:
        host = _bare(urlsplit(site_url).hostname)
    except ValueError:
        host = ''
    if not isinstance(text, str) or not host or '.' not in host:
        return text
    pat = re.compile(r'(?i)(?<![\w@.-])(?:https?://)?(?:www\.)?' + re.escape(host) + r'(?![\w-]|\.\w)(?:/[^\s,;)\]"\'<>]*)?')

    def sub(m):
        before = text[:m.start()].rstrip(' \t')
        start = not before or before[-1] in '.!?\n'
        return GOAL_PHRASE[0].upper() + GOAL_PHRASE[1:] if start else GOAL_PHRASE
    return pat.sub(sub, text)


def protocol(text):
    """The system prompt without the goto action (hidden); unchanged when visible."""
    if not hidden():
        return text
    if GOTO_ACTION not in text:
        raise ValueError('url_visibility=hidden: the protocol no longer lists goto as expected; update GOTO_ACTION')
    return text.replace(GOTO_ACTION, '')


def check_action(choice):
    """Refuse goto when the URL is hidden (raised as a protocol error, so the agent is told and can act again)."""
    if hidden() and isinstance(choice, dict) and choice.get('action') == 'goto':
        raise ValueError('goto is not available; use the page controls, back or forward')
