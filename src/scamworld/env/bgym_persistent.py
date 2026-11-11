"""Make BrowserGym's BrowserEnv launch a persistent Chromium context on a fresh temp profile.

On macOS every Playwright browser that creates a non-persistent context makes `secd` burn
~9 CPU-seconds; a persistent context does not. BrowserEnv.reset() starts two browsers per
episode (the environment and the chat window), so each is proxied here: `launch(**kw)` returns
a handle whose `new_context(**ctx_kw)` calls `launch_persistent_context(<fresh temp dir>, **kw, **ctx_kw)`.
Isolation is unchanged: every episode gets an empty profile that is deleted on close().
Set SCAMWORLD_BGYM_NONPERSISTENT=1 to keep BrowserGym's own browsers. Either way every launch gets the network
isolation arguments (env/browser.py ISOLATION_ARGS).
"""
from __future__ import annotations

import os
import shutil
import tempfile

import browsergym.core.chat as bgchat
import browsergym.core.env as bgenv

from scamworld.env.browser import isolated


class _PersistentBrowser:
    def __init__(self, chromium, launch_kwargs):
        self._chromium, self._lk, self._ctx, self._dir = chromium, launch_kwargs, None, None

    def new_context(self, **ctx_kwargs):
        self._dir = tempfile.mkdtemp(prefix='scamworld-profile-')
        ctx_kwargs = {k: v for k, v in ctx_kwargs.items() if v is not None}
        self._ctx = ctx = self._chromium.launch_persistent_context(self._dir, **self._lk, **ctx_kwargs)
        first = ctx.pages[0] if ctx.pages else ctx.new_page()
        orig = ctx.new_page
        close = ctx.close

        def close_unrouted(*a, **k):   # no route handler may outlive the context (runtime.BrowserRuntime.detach)
            try:
                ctx.unroute_all(behavior='ignoreErrors')
            except Exception:
                pass
            return close(*a, **k)
        ctx.close = close_unrouted

        def new_page_once():  # BrowserEnv asks for its first page right after; hand out the one the launch opened
            ctx.new_page = orig
            return first
        ctx.new_page = new_page_once
        return ctx

    def close(self):
        try:
            if self._ctx:
                self._ctx.close()
        except Exception:
            pass
        if self._dir:
            shutil.rmtree(self._dir, ignore_errors=True)
        self._ctx = self._dir = None


class _Chromium:
    def __init__(self, c, persistent=True):
        self._c, self._persistent = c, persistent

    def launch(self, **kw):
        kw = isolated(kw)   # network isolation for the environment and the chat browser (env/browser.py)
        return _PersistentBrowser(self._c, kw) if self._persistent else self._c.launch(**kw)

    def __getattr__(self, n):
        return getattr(self._c, n)


class _PW:
    def __init__(self, pw, persistent=True):
        self._pw, self._persistent = pw, persistent

    @property
    def chromium(self):
        return _Chromium(self._pw.chromium, self._persistent)

    def __getattr__(self, n):
        return getattr(self._pw, n)


_orig_env = bgenv._get_global_playwright
_orig_chat = bgchat._get_global_playwright


def install():
    """Idempotent: always wraps the original BrowserGym accessors, never an earlier wrapper."""
    if os.environ.get('SCAMWORLD_BGYM_NONPERSISTENT') == '1':   # BrowserGym's own browsers, still network-isolated
        bgenv._get_global_playwright = lambda: _PW(_orig_env(), persistent=False)
        bgchat._get_global_playwright = lambda: _PW(_orig_chat(), persistent=False)
        return
    bgenv._get_global_playwright = lambda: _PW(_orig_env())
    bgchat._get_global_playwright = lambda: _PW(_orig_chat())
