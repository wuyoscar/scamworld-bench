"""Isolated browser contexts for capture versus reconstructed-site screenshots."""
import json
import shutil
import tempfile
from urllib.parse import urlsplit


def _new_context(browser, origin):
    return browser.new_context(viewport={'width': 1280, 'height': 900},
                               java_script_enabled=origin is not None,
                               service_workers='block', accept_downloads=False)


def persistent_comparison_context(playwright, *, executable_path, args=(), origin=None, blocked=None):
    """Same guarded context as comparison_context, opened as a persistent context on a fresh temp profile.

    A non-persistent context makes macOS secd spend several CPU-seconds per browser; a persistent one does not.
    Release it with close_comparison_context(ctx), which also deletes the temp profile.
    """
    profile = tempfile.mkdtemp(prefix='scamworld-profile-')
    ctx = playwright.chromium.launch_persistent_context(
        profile, headless=True, executable_path=executable_path, args=list(args),
        viewport={'width': 1280, 'height': 900}, java_script_enabled=origin is not None,
        service_workers='block', accept_downloads=False)
    ctx._sw_profile_dir = profile
    return _guard(ctx, origin, blocked)


def close_comparison_context(ctx):
    profile = getattr(ctx, '_sw_profile_dir', None)
    try:
        ctx.close()
    finally:
        if profile:
            shutil.rmtree(profile, ignore_errors=True)


def comparison_context(browser, *, origin=None, blocked=None):
    """No original scripts; reconstructed scripts may read only their owned origin.

    The caller supplies a LocalSiteServer origin for a reconstructed site. An
    arbitrary loopback host is not sufficient: other local services are excluded.
    """
    return _guard(_new_context(browser, origin), origin, blocked)


def _guard(ctx, origin, blocked):
    from scamworld.env.runtime import GUARD_JS

    blocked = blocked if blocked is not None else []

    def route(request):
        url = request.request.url
        parsed = urlsplit(url)
        actual_origin = f'{parsed.scheme}://{parsed.netloc}'
        if (origin is not None and actual_origin == origin
                and request.request.method in ('GET', 'HEAD')):
            request.continue_()
        else:
            blocked.append({'url': url, 'method': request.request.method})
            request.abort()

    ctx.route('http*://**', route)
    # Browser-level coverage also applies to frames; init scripts alone can be
    # replaced by a page and are not the network boundary.
    # New Playwright has a socket route; the pinned older runtime relies on
    # LocalSiteServer's connect-src CSP plus GUARD_JS for WebSocket isolation.
    if hasattr(ctx, 'route_web_socket'):
        ctx.route_web_socket('**/*', lambda socket: socket.close())
    if origin is not None:
        ctx.add_init_script(script=f'({GUARD_JS})({json.dumps(origin)})')
    return ctx
