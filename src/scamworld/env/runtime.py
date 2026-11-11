"""Execute browser actions against a single owned loopback origin that serves a task's site/ folder.

By default the observation is a viewport screenshot plus the page's accessibility controls (agents/openrouter.py obs_modes,
docs/custom-agents.md). DOM, internal state, and evidence tags are evaluator artifacts, and never imply that the agent
inspected their contents.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import re
import shutil
import struct
import tempfile
import threading
import zlib
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, urljoin

from scamworld.corpus.annotations_a8 import restore_site_event
from scamworld.corpus.neutral_names import from_served, restore_event, to_served
from scamworld.env import offsite
from scamworld.env.browser import ISOLATION_ARGS, chromium_kwargs

ROUTE_FETCH_MS = 60000   # a locally fulfilled subrequest may take this long; the context's 15 s action timeout left a slow one unresolved, and the page hung
# Playwright calls the route handler for the first URL of a redirect chain only: a 3xx handed to the browser by
# route.fulfill is followed by the browser without the handler. fulfill_fetched never hands one over.
REDIRECT_PAGE = '<!doctype html><meta charset="utf-8"><script>location.replace(%s)</script>'
REDIRECT_HOPS = 5


def fulfill_fetched(route, response, follow=lambda url: False):
    """Fulfill a route.fetch(max_redirects=0) response, never with a redirect (3xx with Location). A navigation gets
    REDIRECT_PAGE, which opens the Location (resolved against the request URL) as a new navigation, routed like any
    other request. Another request follows up to REDIRECT_HOPS hops while follow(url) allows the next one (default: none).
    Returns the redirect target that was refused (the request is then aborted), else None."""
    req, url = route.request, route.request.url
    for _ in range(REDIRECT_HOPS + 1):
        location = response.headers.get('location') if 300 <= response.status < 400 else None
        if not location:
            route.fulfill(response=response)
            return None
        target = urljoin(url, location)
        if urlparse(target).scheme not in ('http', 'https'):
            break
        if req.is_navigation_request():
            route.fulfill(status=200, content_type='text/html; charset=utf-8',
                          body=REDIRECT_PAGE % json.dumps(target).replace('<', '\\u003c'))
            return None
        if not follow(target):
            break
        url, response = target, route.fetch(url=target, max_redirects=0, timeout=ROUTE_FETCH_MS)
    route.abort('blockedbyclient')
    return target


def unreachable_page(url):
    """The page a browser without network shows for an address outside the site (Chromium's words, no product names)."""
    import html as _html
    host = _html.escape(urlparse(url).hostname or url)
    return ('<!doctype html><html><head><meta charset="utf-8"><title>' + host + '</title></head><body>'
            '<h1>This site can\'t be reached</h1><p>' + host + '\'s server IP address could not be found.</p>'
            '<p>ERR_NAME_NOT_RESOLVED</p></body></html>')


START_GOTO_MS = 60000   # setup only: opening the start page is not agent time, so a busy machine gets a generous limit
START_SETTLE_MS = {"load": 30000, "networkidle": 10000}   # then wait for these at most this long; neither fails setup
ANIMATION_SETTLE_MS = 3000   # total wait for running finite CSS animations/transitions before an observation
ANIMATION_SETTLE_JS = """async cap => {
    const end = performance.now() + cap, start = performance.now();
    const running = () => document.getAnimations().filter(a => {
        if (a.playState !== 'running') return false;   // paused or already finished
        if (typeof DocumentTimeline !== 'undefined' && !(a.timeline instanceof DocumentTimeline)) return false;   // scroll-driven
        let t; try { t = a.effect && a.effect.getComputedTiming(); } catch (e) { return false; }
        if (!t || !Number.isFinite(t.endTime)) return false;   // infinite iterations never end: excluded
        const rate = Math.abs(a.playbackRate);
        if (!rate) return false;
        const remaining = (t.endTime - (a.currentTime || 0)) / rate;   // ms left, delay and playback rate included
        return remaining <= end - performance.now();   // longer than the time left (marquees, Ken Burns, slow transitions): not waited for
    });
    const frame = () => Promise.race([new Promise(r => requestAnimationFrame(() => r())), new Promise(r => setTimeout(r, 50))]);
    let passes = 0, list = running();
    while (list.length && performance.now() < end && passes < 6) {
        passes += 1;
        await Promise.race([Promise.allSettled(list.map(a => a.finished)), new Promise(r => setTimeout(r, Math.max(0, end - performance.now())))]);
        await frame();   // let a style recalculation start follow-up transitions/animations; a hidden document cannot hang this
        list = running();
    }
    return {waited_ms: Math.round(performance.now() - start), still_running: list.length, passes};
}"""


def settle_animations(page, cap_ms=ANIMATION_SETTLE_MS):
    """Wait until the page's running finite CSS animations and transitions (delays included) have finished, at most
    cap_ms in all, so the first observation of a page with delayed entrance animations is not taken while its content is
    still at opacity 0 (e.g. every block fading in with 0.6-1.3 s delays). Infinite animations are not waited for. Never
    raises: a page that is gone or replaced mid-wait just returns None. Returns {waited_ms, still_running, passes}."""
    try:
        return page.evaluate(ANIMATION_SETTLE_JS, cap_ms)
    except Exception:
        return None


def open_start_page(page, url):
    """Open the start page, then wait for its load event and for network idle, each bounded (a goto that
    waited for networkidle under the 15 s action timeout could fail at setup on a busy machine although the site loaded
    in other episodes; the route handler serves subrequests one at a time). The page
    is still observed only once observe_stable_document finds it stable. Returns what the waits reached, for the trace."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
    page.goto(url, wait_until="domcontentloaded", timeout=START_GOTO_MS)
    reached = {"url": url, "domcontentloaded": True}
    for state, limit in START_SETTLE_MS.items():
        try:
            page.wait_for_load_state(state, timeout=limit)
            reached[state] = True
        except PlaywrightTimeout:
            reached[state] = False
    reached["animations"] = settle_animations(page)
    return reached


def late_charset_utf8(path) -> bool:
    """True for an HTML file that needs charset=utf-8 in its Content-Type: UTF-8 bytes with non-ASCII text and no charset
    declaration in the first 1024 bytes, Chromium's prescan window (e.g. a meta tag at byte 6859 leaves the page decoded as
    windows-1252, "Â© 2023"). Every other file keeps its type."""
    try:
        data = Path(path).read_bytes()
    except OSError:
        return False
    if data.isascii() or b'charset' in data[:1024].lower():
        return False
    try:
        data.decode('utf-8')
    except UnicodeDecodeError:
        return False
    return True


def _transparent_png():
    """A 1x1 fully transparent RGBA PNG."""
    chunk = lambda kind, data: struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00\x00\x00\x00\x00')) + chunk(b'IEND', b''))


# A resource the capture lost is served at pics/<hash> (corpus.neutral_names; __missing__/ in the task files). Generated
# images stand in for the <img> and inline-background images that show; any other missing one
# (mostly CSS backgrounds) answers 200 with a transparent 1x1 PNG instead of a 404, as a CDN placeholder would.
MISSING_DIR = '/pics/'
TRANSPARENT_PNG = _transparent_png()


SERVER_CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
              "font-src 'self' data:; connect-src 'self'; worker-src 'none'; frame-src 'self'; form-action 'none'; base-uri 'self'; object-src 'none'")
PAGE_CSP_META = re.compile(rb'<meta\b[^>]*http-equiv\s*=\s*["\']?content-security-policy["\']?[^>]*>\s*', re.I)


_HEAD_CONTENT = {b'html', b'head', b'meta', b'title', b'link', b'style', b'script', b'base', b'noscript', b'template'}


def meta_in_head(html, start):
    """Whether an HTML parser keeps the element at byte offset `start` in <head> (only there does a CSP meta take effect):
    nothing but a doctype, comments, whitespace and head content (the contents of script/style/title/noscript/template
    skipped) may come before it, and no </head> or </html>. A body element or text before it opens <body>."""
    pre = html[:start]
    pre = re.sub(rb'^\xef\xbb\xbf', b'', pre)
    pre = re.sub(rb'<!--.*?-->', b'', pre, flags=re.S)
    pre = re.sub(rb'<!doctype[^>]*>', b'', pre, flags=re.I)
    pre = re.sub(rb'<(script|style|title|noscript|template)\b[^>]*>.*?</\1\s*>', b'', pre, flags=re.S | re.I)
    for m in re.finditer(rb'<\s*(/?)\s*([a-zA-Z][a-zA-Z0-9-]*)[^>]*>|([^<]+)', pre):
        if m.group(3) is not None:
            if m.group(3).strip():
                return False
        elif m.group(1):
            if m.group(2).lower() in (b'head', b'html'):
                return False
        elif m.group(2).lower() not in _HEAD_CONTENT:
            return False
    return True


class _QuietHandler(SimpleHTTPRequestHandler):
    # Answer like an ordinary web server (no Python/SimpleHTTP banner, no directory listings, plain 404 page).
    # A link to a page the capture never had keeps its original path (corpus/dead_links_a6e.py), and this
    # 404 is what a click on it shows, for every site alike. `unavailable`: request keys answered 404 although their path is
    # served (the site root with a query); the server of a task gets them from its records/a6e-dead-links.json.
    unavailable = frozenset()
    error_message_format = ('<html>\r\n<head><title>%(code)d %(message)s</title></head>\r\n<body>\r\n'
                            '<center><h1>%(code)d %(message)s</h1></center>\r\n<hr><center>nginx</center>\r\n</body>\r\n</html>\r\n')
    responses = {**SimpleHTTPRequestHandler.responses, 404: ('Not Found', ''), 501: ('Not Implemented', '')}

    def version_string(self):
        return "nginx"

    def list_directory(self, path):
        self.send_error(404)
        return None

    def send_error(self, code, message=None, explain=None):
        super().send_error(code, None, None)   # standard reason phrase only ("File not found" is Python's wording)

    def log_message(self, *_):
        pass

    def send_head(self):
        path = urlparse(self.path).path
        if self.unavailable:
            from scamworld.corpus.dead_links_a6e import request_key
            if request_key(self.path) in self.unavailable:
                self.send_error(404)
                return None
        if MISSING_DIR in path and not path.endswith('/') and not os.path.isfile(self.translate_path(self.path)):
            self.send_response(200)
            self.send_header('Content-Type', 'image/png')
            self.send_header('Content-Length', str(len(TRANSPARENT_PNG)))
            self.end_headers()
            return io.BytesIO(TRANSPARENT_PNG)
        page = self._html_file(path)
        if page:
            return self._send_page(page)
        return super().send_head()

    def _html_file(self, path):
        """The HTML file a GET of path serves (a directory with its slash serves its index), else None."""
        local = self.translate_path(self.path)
        if os.path.isdir(local):
            if not path.endswith('/'):
                return None   # SimpleHTTPRequestHandler's 301 to path/ (fulfill_fetched never hands it to the browser)
            local = next((os.path.join(local, i) for i in ('index.html', 'index.htm') if os.path.isfile(os.path.join(local, i))), None)
        return local if local and local.lower().endswith(('.html', '.htm')) and os.path.isfile(local) else None

    def _send_page(self, local):
        # A page's own <meta http-equiv=Content-Security-Policy> is sent as a response header instead, as a
        # real server would, and taken out of the served HTML, so an agent reading the page source (html observation) does not
        # see a sandbox policy (form-action 'none', connect-src 'none'). The policy in force is unchanged: the header carries the
        # server policy and the page policy together (a comma joins policies that are all enforced), and in every task page the
        # meta is the first policy-relevant element of <head>, so nothing it governs loaded before it.
        body = Path(local).read_bytes()
        m = PAGE_CSP_META.search(body)
        self._page_csp = None
        if m:
            c = re.search(rb'content\s*=\s*"([^"]*)"', m.group(0)) or re.search(rb"content\s*=\s*'([^']*)'", m.group(0))
            if c:
                # a meta the HTML parser puts in <body> was never enforced (travel-01: a <div> before <head>); it is removed
                # without becoming a header, so nothing that ran before stops running
                if meta_in_head(body, m.start()):
                    self._page_csp = c.group(1).decode('utf-8', 'replace').strip()
                body = body[:m.start()] + body[m.end():]
        self.send_response(200)
        self.send_header('Content-Type', self.guess_type(local))
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        return io.BytesIO(body)

    def guess_type(self, path):
        ctype = super().guess_type(path)
        return 'text/html; charset=utf-8' if ctype == 'text/html' and late_charset_utf8(path) else ctype

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        page = getattr(self, '_page_csp', None)
        self._page_csp = None
        self.send_header("Content-Security-Policy", SERVER_CSP + (', ' + page if page else ''))
        super().end_headers()


class LocalSiteServer:
    """Serve one materialized case; no API accepts external writes."""

    def __init__(self, site_dir: str | Path, unavailable=frozenset()):
        self.site_dir = Path(site_dir).resolve()
        if not self.site_dir.is_dir():
            raise ValueError(f"Missing site directory: {self.site_dir}")
        # Symlinks could escape the case directory through SimpleHTTPRequestHandler.
        if any(p.is_symlink() for p in self.site_dir.rglob("*")):
            raise ValueError("Site artifacts must not contain symlinks")
        handler = type('_SiteHandler', (_QuietHandler,), {'unavailable': frozenset(unavailable)}) if unavailable else _QuietHandler
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), partial(handler, directory=str(self.site_dir)))
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


# Runs before site scripts: logs actual dispatch and blocks browser transports
# beyond the one owned origin. Server accepts only static GET/HEAD.
GUARD_JS = """(origin) => {
  const originalFetch=window.fetch;
  window.__pagekitRuntimeEvents=[];
  window.__pagekitDrainEvents=()=>window.__pagekitRuntimeEvents.splice(0);
  const record=(type,detail)=>window.__pagekitRuntimeEvents.push({type,...detail});
  const allowed=u=>{try{return new URL(u,location.href).origin===origin}catch{return false}};
  window.fetch=(u,o={})=>{const url=String(u.url||u); if(!allowed(url)){
    record('boundary_attempt',{url,transport:'fetch'}); return Promise.reject(Error('External request blocked'));
  } return originalFetch(u,o);};
  const send=XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open=function(method,url,...rest){if(!allowed(url)){
    record('boundary_attempt',{url:String(url),transport:'xhr'});throw Error('External request blocked');
  } return send.call(this,method,url,...rest)};
  navigator.sendBeacon=(url)=>{record('boundary_attempt',{url:String(url),transport:'beacon'});return false;};
  window.WebSocket=class {constructor(url){record('boundary_attempt',{url:String(url),transport:'websocket'});throw Error('WebSocket disabled');}};
  window.EventSource=class {constructor(url){record('boundary_attempt',{url:String(url),transport:'eventsource'});throw Error('EventSource disabled');}};
  window.Worker=window.SharedWorker=class {constructor(url){record('boundary_attempt',{url:String(url),transport:'worker'});throw Error('Workers disabled');}};
  window.RTCPeerConnection=window.webkitRTCPeerConnection=class {constructor(){record('boundary_attempt',{transport:'webrtc'});throw Error('WebRTC disabled');}};
  document.addEventListener('securitypolicyviolation',e=>record('boundary_attempt',{url:e.blockedURI,transport:'csp',directive:e.effectiveDirective}));
  document.addEventListener('click',e=>{const a=e.target.closest('a');if(a&&!allowed(a.href)){
    e.preventDefault();record('boundary_attempt',{url:a.href,transport:'link'});
  }},true);
  document.addEventListener('submit',e=>{e.preventDefault();record('form_submit_attempt',{
    target:e.target.id||null,action:e.target.action,transport:'form',simulated:true});},true);
  document.addEventListener('click',e=>{const el=e.target.closest('[data-action-id],button,a,input[type=submit],input[type=image]');if(el)record('dom_action',{
    action:'click',target:el.dataset.actionId||el.id||null,form_id:el.form&&el.form.id||null,control_type:el.type||null});},true);
  document.addEventListener('input',e=>record('dom_action',{action:'type_fixture_text',target:e.target.id||null,value:e.target.value}),true);
  document.addEventListener('change',e=>record('dom_action',{action:'select_option',target:e.target.id||null}),true);
}"""

EVIDENCE_JS = """() => Array.from(document.querySelectorAll('[data-evidence-id]')).map(el=>{
 const r=el.getBoundingClientRect(),s=getComputedStyle(el);
 let x=Math.max(0,r.x),y=Math.max(0,r.y),right=Math.min(innerWidth,r.right),bottom=Math.min(innerHeight,r.bottom),painted=true;
 for(let p=el;p;p=p.parentElement){const ps=getComputedStyle(p),pr=p.getBoundingClientRect();
  if(ps.display==='none'||ps.visibility==='hidden'||Number(ps.opacity)===0)painted=false;
  if(p!==el&&['hidden','clip','scroll','auto'].includes(ps.overflowX)){x=Math.max(x,pr.x);right=Math.min(right,pr.right)}
  if(p!==el&&['hidden','clip','scroll','auto'].includes(ps.overflowY)){y=Math.max(y,pr.y);bottom=Math.min(bottom,pr.bottom)}
 }
 const area=Math.max(0,right-x)*Math.max(0,bottom-y),visible=area>0&&painted;
 // Conservatively reject an anchor when any of five interior samples is occluded.
 const points=[[.5,.5],[.05,.05],[.95,.05],[.05,.95],[.95,.95]];
 const unoccluded=visible&&points.every(([px,py])=>{const hit=document.elementFromPoint(x+(right-x)*px,y+(bottom-y)*py);return hit&&(hit===el||el.contains(hit))});
 return {evidence_id:el.dataset.evidenceId,text:el.innerText||el.textContent||'',bbox:{x:r.x,y:r.y,width:r.width,height:r.height},
 viewport_bbox:{x,y,width:Math.max(0,right-x),height:Math.max(0,bottom-y)},visible:visible&&unoccluded,
 visible_fraction:r.width*r.height?area/(r.width*r.height):0,inspection_status:'exposed_only'};
})"""


class BrowserRuntime:
    def __init__(self, site_dir: str | Path, artifact_dir: str | Path, *, case_id: str,
                 start_path="/index.html", viewport=None, executable_path=None, observation_track="screenshot", unavailable=frozenset()):
        self.site_dir, self.artifact_dir = Path(site_dir).resolve(), Path(artifact_dir).resolve()
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.case_id, self.start_path = case_id, start_path
        self.viewport = viewport or {"width": 1280, "height": 720}
        # SCAMWORLD_CHROME_PATH if set (the published runs used Chrome for Testing 155 on Linux x86_64), else the Mac
        # Chrome app, else the Playwright browser
        self.executable_path = executable_path or chromium_kwargs().get("executable_path")
        self.observation_track = observation_track
        self.server = LocalSiteServer(self.site_dir, unavailable)
        self.pw = self.browser = self.context = self.page = self._profile_dir = None
        self.observations, self.actions, self.events = [], [], []
        self.terminated = False
        self.episode_id = 0
        self.final_answer = None
        self.environment_errors = []
        self.carried_events = []   # events drained from a page just before its slow navigation replaced it
        self._closing = False      # set by detach(): route errors of a context being closed are expected

    def _allowed(self, url):
        parsed = urlparse(url)
        return (parsed.scheme == "http" and parsed.hostname == "127.0.0.1" and parsed.port == self.server.server.server_port) \
            or (offsite.on() and offsite.kind(url) is not None)   # experiment option offsite (env/offsite.py); off by default

    def _route_offsite(self, route):
        """Experiment option offsite (env/offsite.py), ahead of the usual routing: True when it settled the request. Off: False,
        nothing read. An allowlisted request is fetched by the harness and fulfilled by fulfill_fetched, so a redirect comes
        back here as a new navigation; a request from an allowlisted page to any other host except the site is blocked (a
        main-frame navigation shows offsite.NEUTRAL_PAGE). Everything else is routed as in every run."""
        if not offsite.on():
            return False
        req = route.request
        try:
            frame = req.frame
            from_url, main = frame.url, frame.parent_frame is None
        except Exception:   # e.g. a service-worker request has no frame
            from_url, main = '', False
        navigation = req.is_navigation_request() and main
        if offsite.allowed(req.url, req.method):
            if navigation:
                self.events.append({"type": "offsite_visit", "url": req.url, "host": urlparse(req.url).hostname,
                                    "kind": offsite.kind(req.url), "method": req.method, "step": len(self.actions) + 1})
            from playwright.sync_api import Error as PlaywrightError
            try:
                response = route.fetch(max_redirects=0, timeout=ROUTE_FETCH_MS)
                if offsite.challenge(response):   # a bot challenge is never shown or solved
                    self.events.append({"type": "offsite_challenge", "url": req.url, "host": urlparse(req.url).hostname,
                                        "status": response.status, "step": len(self.actions) + 1})
                    if navigation:
                        route.fulfill(status=200, content_type="text/html; charset=utf-8", body=offsite.NEUTRAL_PAGE)
                    else:
                        route.abort("blockedbyclient")
                    return True
                refused = fulfill_fetched(route, response, offsite.allowed)
            except PlaywrightError as e:   # the external site did not answer: a failed page load, not an environment error
                if self._closing or type(e).__name__ == 'TargetClosedError' or 'has been closed' in str(e):
                    raise
                self.events.append({"type": "offsite_fetch_failed", "url": req.url, "method": req.method,
                                    "message": str(e)[:300], "step": len(self.actions) + 1})
                route.abort("failed")
                return True
            if refused:   # a subresource redirected outside the allowlist
                self.events.append({"type": "boundary_attempt", "url": refused, "method": "GET", "transport": "redirect",
                                    "blocked": True, "offsite_page": True, "step": len(self.actions) + 1})
            return True   # a context closed meanwhile: _guarded_route drops the error (detach)
        if offsite.kind(from_url) is None or self._allowed(req.url):
            return False
        self.events.append({"type": "boundary_attempt", "url": req.url, "method": req.method, "transport": "network",
                            "blocked": True, "offsite_page": True, "step": len(self.actions) + 1})
        if navigation:
            route.fulfill(status=200, content_type="text/html; charset=utf-8", body=offsite.NEUTRAL_PAGE)
        else:
            route.abort("blockedbyclient")
        return True

    def _guarded_route(self, route):
        """The context's route handler: _route, except that a Playwright error of a context being closed is dropped. Any other
        route error is recorded in environment_errors, the request is aborted, and the error is re-raised."""
        from playwright.sync_api import Error as PlaywrightError
        try:
            self._route(route)
        except PlaywrightError as e:
            if self._closing or type(e).__name__ == 'TargetClosedError' or 'has been closed' in str(e):
                return
            self.environment_errors.append({'type': 'route_error', 'url': route.request.url, 'message': str(e)[:500]})
            try:   # settle the request, so the page does not wait on it until the next timeout
                route.abort('failed')
            except Exception:
                pass
            raise

    def detach(self):
        """Before the context or page closes: remove the route handler and drop the errors of handlers still running. A
        route.fetch that fails because its context closed is otherwise kept by Playwright's sync API and raised by the next
        call on the same Playwright instance, i.e. the next episode's launch_persistent_context (BrowserGym shares one
        Playwright per process)."""
        self._closing = True
        if self.context is not None:
            try:
                self.context.unroute_all(behavior='ignoreErrors')
            except Exception:
                pass

    def _route(self, route):
        if self._route_offsite(route):
            return
        req = route.request
        if self._allowed(req.url) and req.method in ("GET", "HEAD"):
            route.continue_()
        else:
            self._refuse(route)

    def _refuse(self, route):
        """A request outside the site: recorded as boundary_attempt and never sent. A top-level navigation (a goto, a
        script's location change) shows unreachable_page(url) at that address, as a browser without network does, rather
        than refusing a goto before it runs (the agent would keep the site page, or an empty new tab, with an error)."""
        req = route.request
        self.events.append({"type": "boundary_attempt", "url": req.url, "method": req.method,
                            "transport": "network", "blocked": True, "step": len(self.actions) + 1})
        try:
            main = req.is_navigation_request() and req.frame.parent_frame is None
        except Exception:   # e.g. a service-worker request has no frame
            main = False
        if main and not offsite.on():
            route.fulfill(status=200, content_type="text/html; charset=utf-8", body=unreachable_page(req.url))
        else:
            route.abort("blockedbyclient")

    def attach(self, page):
        """Attach guards to a fresh BrowserGym-owned context before navigation."""
        self.page, self.context = page, page.context
        self._closing = False
        self.context.route("**/*", self._guarded_route)
        self.context.on("response", self._not_found)
        self.context.add_init_script(offsite.init_script(GUARD_JS, self.server.origin))
        self.page.on("dialog", lambda dialog: dialog.dismiss())
        self.page.on("pageerror", lambda error: self.environment_errors.append({"type":"pageerror","message":str(error)}))
        self.context.on("page", self._new_page)
        self.page.on("download", lambda download: download.cancel())

    def _not_found(self, response):
        """A main-frame navigation the server answered 404 (a page the capture never had) is recorded as a
        runtime event; score.py's dead_link reads it."""
        try:
            if response.status == 404 and response.request.is_navigation_request() and response.frame.parent_frame is None:
                self.events.append({"type": "not_found", "url": response.url, "step": len(self.actions)})
        except Exception:   # a response without a frame (service worker) or of a page being closed
            pass

    def _new_page(self, page):
        page.on("dialog", lambda dialog: dialog.dismiss())
        page.on("pageerror", lambda error: self.environment_errors.append({"type":"pageerror","message":str(error)}))
        page.on("download", lambda download: download.cancel())

    def _close_context(self):
        if self.context:
            self.detach()
            try: self.context.close()
            except Exception: pass
        self.context = None
        if self._profile_dir:
            shutil.rmtree(self._profile_dir, ignore_errors=True)
            self._profile_dir = None

    def reset(self, *, seed=0):
        from playwright.sync_api import sync_playwright
        self._close_context()
        if not self.pw:
            self.pw = sync_playwright().start()
        self.episode_id += 1
        self.seed = seed
        self.observations, self.actions, self.events = [], [], []
        self.terminated = False
        self.final_answer = None
        self.environment_errors = []
        # A fresh persistent profile per episode: same isolation as a new browser, but launching an
        # incognito context makes macOS secd burn ~9 CPU-seconds on every browser.
        self._profile_dir = tempfile.mkdtemp(prefix="scamworld-profile-")
        self.context = self.pw.chromium.launch_persistent_context(
            self._profile_dir, headless=True, executable_path=self.executable_path,
            args=["--disable-background-networking","--force-webrtc-ip-handling-policy=disable_non_proxied_udp","--use-mock-keychain","--password-store=basic"] + ISOLATION_ARGS,
            viewport=self.viewport, service_workers="block", accept_downloads=False)
        self.attach(self.context.pages[0] if self.context.pages else self.context.new_page())
        url=urljoin(self.server.origin,self.start_path)
        if not self._allowed(url):raise ValueError('Start path must use the owned loopback origin')
        self.start_page_wait = open_start_page(self.page, url)
        return self.observe(), {"case_id": self.case_id, "seed": seed, "network": "owned_loopback_origin_only"}

    def _interaction_regions(self):
        anchors=[{'id':a['id'],'selector':to_served(a['selector'])} for a in getattr(self,'private_anchors',[]) if a.get('type')=='interaction_region']
        return self.page.evaluate("""(anchors)=>{
          function rendered(e){if(!e||!Array.from(e.getClientRects()).some(r=>r.width>0&&r.height>0))return false;for(let p=e;p;p=p.parentElement){const s=getComputedStyle(p);if(s.display==='none'||s.visibility==='hidden'||Number(s.opacity)===0)return false;}return true;}
          function viewport(e){
            const r=e.getBoundingClientRect();let left=Math.max(0,r.left),top=Math.max(0,r.top),right=Math.min(innerWidth,r.right),bottom=Math.min(innerHeight,r.bottom);
            for(let p=e.parentElement;p&&p!==document.documentElement;p=p.parentElement){const s=getComputedStyle(p),q=p.getBoundingClientRect();
              if(['hidden','clip','scroll','auto'].includes(s.overflowX)){left=Math.max(left,q.left+p.clientLeft);right=Math.min(right,q.left+p.clientLeft+p.clientWidth);}
              if(['hidden','clip','scroll','auto'].includes(s.overflowY)){top=Math.max(top,q.top+p.clientTop);bottom=Math.min(bottom,q.top+p.clientTop+p.clientHeight);}}
            const area=Math.max(0,right-left)*Math.max(0,bottom-top),fraction=rendered(e)&&r.width*r.height>0?Math.min(1,area/(r.width*r.height)):0;
            return {version:'region_viewport_geometry_v1',bbox:{x:r.x,y:r.y,width:r.width,height:r.height},viewport:{width:innerWidth,height:innerHeight},visible_fraction:fraction,fully_visible:rendered(e)&&r.width>0&&r.height>0&&fraction>=1-1e-9,occlusion_checked:false};
          }
          return anchors.map(a=>({region_id:a.id,matches:Array.from(document.querySelectorAll(a.selector)).map(e=>({rendered:rendered(e),input_count:e.querySelectorAll('input,textarea').length,rendered_input_count:Array.from(e.querySelectorAll('input,textarea')).filter(rendered).length,viewport_geometry:viewport(e)}))}));
        }""",anchors)

    def _state(self):
        return {"url": self.page.url, "state_id": self.page.evaluate("document.body ? document.body.dataset.stateId || null : null"),
                "scroll": self.page.evaluate("({x:scrollX,y:scrollY})"),
                "values": self.page.evaluate("Array.from(document.querySelectorAll('input,select,textarea')).map(e=>({id:e.id,value:e.value}))"),
                "interaction_regions": self._interaction_regions(),
                "form_controls": self.page.evaluate("""() => Array.from(document.querySelectorAll('input,select,textarea,button')).map(e=>({id:e.id,name:e.name,tag:e.tagName.toLowerCase(),type:e.type,value:e.value,checked:!!e.checked,disabled:!!e.disabled,form_id:e.form&&e.form.id,rendered:e.getClientRects().length>0&&getComputedStyle(e).visibility!=='hidden'}))"""),
                # An opaque-origin page (about:blank after new_tab or closing the last tab, an error page) denies storage access.
                "storage": self.page.evaluate("(() => { try { return Object.fromEntries(Object.entries(localStorage)); } catch (e) { return {}; } })()"),
                # Rendered viewport text is telemetry, never a task postcondition.
                "public_content": [{"text": row["text"]} for row in self.page.evaluate(
                    EVIDENCE_JS.replace("[data-evidence-id]", "body *:not(:has(*)):not(script):not(style):not(noscript)"))
                    if row["visible"] and row["visible_fraction"] >= 0.95]}


    # Boundary: the task files, scoring and traces share one set of names (sw-*, risk_commit, /__uncaptured__/...);
    # the served sites carry neutral names (corpus/neutral_names.py). Hidden selectors are mapped to the names served to the
    # page when they meet the page, and what the page reports back (events) is mapped back to the names in the task files here.
    def _site_event(self, event):
        """A site event in the names the task files and recorded traces use: event id and ids in the payload restored, payload
        fields removed from the served flow.js put back."""
        return restore_site_event(self.site_dir, restore_event(event))

    @staticmethod
    def _guard_event(event):
        """Harness events carry ids and the form action read from the page: map those back (never typed values)."""
        keys = {'dom_action': ('target', 'form_id'), 'form_submit_attempt': ('target', 'action')}.get(event.get('type'), ())
        return {**event, **{k: from_served(event[k]) for k in keys if isinstance(event.get(k), str)}}

    def _drain_events(self):
        for event in self.carried_events:
            event = self._site_event(event) if event.get("source") == "site_instrumentation" else self._guard_event(event)
            self.events.append({**event, "step": len(self.actions)})
        self.carried_events = []
        for page in self.context.pages:
            if self._allowed(page.url):
                for event in page.evaluate("window.__pagekitDrainEvents ? window.__pagekitDrainEvents() : []"):
                    self.events.append({**self._guard_event(event), "step": len(self.actions), "url_observed": page.url})
                for event in page.evaluate("window.__pagekitDrainSiteEvents ? window.__pagekitDrainSiteEvents() : []"):
                    self.events.append({**self._site_event(event), "step": len(self.actions), "url_observed": page.url, "source": "site_instrumentation"})

    def observe(self):
        # Both drain functions consume queues. A context failure during this
        # phase has an unknown delivery outcome and must not be retried as a
        # successful empty observation. Later read failures can safely retain
        # the events already received in Python.
        self.page.evaluate("async step => { window.__pagekitCarouselStep?.(step, window.__pagekitStatic === true); if (window.__pagekitCarouselReady) await window.__pagekitCarouselReady; }", len(self.actions))
        self.observation_events_received = False
        self._drain_events()
        self.observation_events_received = True
        oid = f"ep{self.episode_id:04d}-obs{len(self.observations):04d}"
        shot, dom = self.artifact_dir / f"{oid}.png", self.artifact_dir / f"{oid}.html"
        self.page.screenshot(path=str(shot), full_page=False)
        dom.write_text(self.page.content(), encoding="utf-8")
        evidence = self.page.evaluate(EVIDENCE_JS)
        state = self._state()
        if not state['state_id'] and not any(e.get('type')=='missing_state_id' for e in self.environment_errors):
            self.environment_errors.append({'type':'missing_state_id','url':self.page.url})
        record = {"observation_id": oid, "case_id": self.case_id, "state_id": state["state_id"], "url": self.page.url,
                  "step_id": len(self.actions),
                  "screenshot_path": str(shot), "screenshot_sha256": hashlib.sha256(shot.read_bytes()).hexdigest(),
                  "dom_path": str(dom), "dom_sha256": hashlib.sha256(dom.read_bytes()).hexdigest(),
                  "viewport": self.viewport, "visible_evidence": [e for e in evidence if e["visible"] and e["visible_fraction"] >= 0.95],
                  "evidence_regions": evidence, "inspection_inferred": False, "state": state,
                  "track": self.observation_track}
        self.observations.append(record)
        self._save()
        # No DOM/internal state/evidence identifiers in the primary agent channel.
        return {k: record[k] for k in ("observation_id", "step_id", "url", "screenshot_path", "screenshot_sha256", "viewport", "track")}

    def step(self, action: dict):
        """Execute one action directly on the page and observe after 80 ms. Not the agent's path: episodes and
        `scamworld verify` go through BrowserGym (FormalBrowserEnv.step), which waits its pre_observation_delay (0.5 s) and
        then for domcontentloaded before every observation. After 80 ms a click that navigates still shows a partial page
        on many sites, so a harness that calls this directly must wait at least 0.5 s itself before it reads the page."""
        if self.terminated:
            raise RuntimeError("Episode already terminated; reset before another action")
        before = self._state()
        entry = {"step": len(self.actions) + 1, "proposed_action": copy.deepcopy(action), "executed_action": None,
                 "state_before": before, "error": None, "status": "attempted"}
        self.actions.append(entry)
        event_start = len(self.events)
        try:
            kind = action.get("type", action.get("action"))
            target = action.get("target")
            if kind in ("fill", "type"): kind = "type_text"
            if kind in ("click", "type_fixture_text", "type_text", "select_option"):
                if not isinstance(target, str) or not target:
                    raise ValueError("Target must be an observed DOM id")
                # IDs only, no executable CSS or arbitrary browser code.
                locator = self.page.locator("[id=" + json.dumps(target) + "]")
                if locator.count() != 1:
                    raise ValueError(f"Target must identify one element: {target}")
                if kind == "click": locator.click(timeout=3000)
                elif kind in ("type_fixture_text", "type_text"):
                    value = action.get("value", "")
                    if not isinstance(value, str) or kind == "type_fixture_text" and len(value) > 512:
                        raise ValueError("Text must be a string of at most 512 characters")
                    locator.fill(value, timeout=3000)
                else: locator.select_option(action["value"], timeout=3000)
            elif kind in ("press", "keyboard_press"):
                key = action.get("key", action.get("value"))
                if not isinstance(key, str) or not key: raise ValueError("Nonempty browser key combination required")
                if target:
                    self.page.locator("[id=" + json.dumps(target) + "]").press(key, timeout=3000)
                else: self.page.keyboard.press(key)
            elif kind == "click_coordinate":
                x,y = action["x"],action["y"]
                if not 0 <= x < self.viewport["width"] or not 0 <= y < self.viewport["height"]:
                    raise ValueError("Coordinates must be in the viewport")
                entry['resolved_target']=self.target_at_point(x,y)
                self.page.mouse.click(x,y)
            elif kind == "scroll": self.page.mouse.wheel(action.get("dx",0), action.get("dy",500))
            elif kind == "back": self.page.go_back(wait_until="domcontentloaded")
            elif kind == "forward": self.page.go_forward(wait_until="domcontentloaded")
            elif kind == "open_local_url":
                url = urljoin(self.server.origin, action["url"])
                if not self._allowed(url):
                    self.events.append({"type":"boundary_attempt","url":url,"transport":"action","blocked":True,"step":entry["step"]})
                    raise ValueError(offsite.BLOCKED_ERROR if offsite.on() else "Only the owned loopback origin is allowed")
                self.page.goto(url,wait_until="domcontentloaded")
            elif kind == "switch_tab":
                candidate = self.context.pages[action["index"]]
                if not self._allowed(candidate.url): raise ValueError("Tab is outside the owned origin")
                self.page = candidate
            elif kind == "final_answer":
                self.final_answer = copy.deepcopy(action.get("value", action.get("answer")))
                self.terminated = True
            else: raise ValueError(f"Unsupported action: {kind}")
            entry["executed_action"],entry["status"] = copy.deepcopy(action),"executed"
        except Exception as exc:
            entry["error"],entry["status"] = str(exc),"failed"
        self.page.wait_for_timeout(80)
        observation = self.observe()
        after = self._state()
        entry.update(state_after=after, transition_observed=before != after, observation_id=observation["observation_id"],
                     events=copy.deepcopy(self.events[event_start:]))
        self._save()
        return observation, 0.0, self.terminated, False, {"action_record": entry}

    # Intermediate checkpoints run several times per step. Re-serializing every
    # recorded accessibility payload made them O(steps^2) on large pages.
    # Final traces (teardown, export_trace callers) still carry the full payloads.
    CHECKPOINT_OMIT = ("public_accessibility_nodes","accessibility_tree_links","public_accessibility_text","public_accessibility_controls")

    def _save(self):
        full = self.observations
        self.observations = [{k:v for k,v in r.items() if k not in self.CHECKPOINT_OMIT} for r in full]
        try:
            trace = self.export_trace()
        finally:
            self.observations = full
        trace["checkpoint"] = "accessibility payloads omitted; full trace written at teardown"
        (self.artifact_dir / "trace.json").write_text(json.dumps(trace, indent=2),encoding="utf-8")

    def target_at_point(self,x,y):
        return self.page.evaluate("([x,y])=>{const hit=document.elementFromPoint(x,y);const el=hit&&hit.closest('[data-action-id],button,a,input,select,textarea');return el?(el.dataset.actionId||el.id||null):null;}",[x,y])

    def export_trace(self):
        def observation(record):
            return {"state_id":record["state_id"],"visible_evidence_ids":[e["evidence_id"] for e in record["visible_evidence"]],
                    "visible_text_evidence":{e["evidence_id"]:e["text"] for e in record["visible_evidence"]},
                    "screenshot_path":record["screenshot_path"],"dom_path":record["dom_path"],
                    "screenshot_sha256":record["screenshot_sha256"],"observation_id":record["observation_id"],
                    "evidence_regions":record["evidence_regions"],"url":record["url"],"inspection_inferred":False}
        indexed = {o["observation_id"]:o for o in self.observations}
        steps = []
        if self.observations:
            first=self.observations[0]
            steps.append({"step_id":0,"action":{"type":"reset"},"execution":"succeeded","before_state_id":None,
                          "after_state_id":first["state_id"],"observation":observation(first),"events":[]})
        for action in self.actions:
            obs=indexed.get(action.get("observation_id"))
            if obs is None: continue
            proposed=copy.deepcopy(action["proposed_action"])
            if "action" in proposed: proposed["type"]=proposed.pop("action")
            if proposed.get('type')=='click_coordinate' and action.get('resolved_target'):
                proposed.update(type='click',target=action['resolved_target'],raw_type='click_coordinate')
            trusted=[e for e in action.get("events",[]) if e.get("source")=="site_instrumentation" and e.get("event_id")]
            execution={"executed":"succeeded","failed":"failed","not_executed":"not_executed"}.get(action["status"],"not_executed")
            steps.append({"step_id":action["step"],"action":proposed,"execution":execution,
                          "before_state_id":action["state_before"]["state_id"],"after_state_id":action["state_after"]["state_id"],
                          "observation":observation(obs),"events":trusted,"error":action["error"],
                          "transition_observed":action["transition_observed"],
                          **({"agent_notes":action["agent_notes"]} if action.get("agent_notes") else {})})   # a11
            if action.get("raw_action_error"):   # "error" is what the agent was told (None: nothing); the raw text stays here
                steps[-1].update(raw_action_error=action["raw_action_error"], action_error_suppressed=not action["error"])
        return {"schema_version":"0.1", "case_id":self.case_id,"run_id":f"{self.case_id}-ep{self.episode_id:04d}",
                "status":"environment_error" if self.environment_errors else "completed" if self.terminated else "running",
                "steps":steps,"final_answer":copy.deepcopy(self.final_answer),"environment_errors":self.environment_errors,
                "runtime_diagnostics":{"observations":copy.deepcopy(self.observations),"actions":copy.deepcopy(self.actions),
                                       "events":copy.deepcopy(self.events),"network_policy":"owned_loopback_origin_only",
                                       **({"offsite":{"mode":offsite.mode(),"hosts":copy.deepcopy(offsite.HOSTS)}} if offsite.on() else {}),
                                       "start_page":copy.deepcopy(getattr(self,"start_page_wait",None))}}

    def close(self):
        self._close_context()
        if self.pw: self.pw.stop()
        self.server.close()

    def __enter__(self): return self
    def __exit__(self,*_): self.close()
