"""Opt-in local replay of source schemes and exact captured navigation targets.

Declared browser URLs retain their original origin. Every request is fulfilled
from the owned static server; this never authorizes an external network request.
"""
from urllib.parse import urlparse, urlsplit, unquote


def navigation_routes(items):
    """Validate finite exact destination→local-file mappings, without wildcards."""
    if not isinstance(items, list) or not items or len(items) > 20:
        raise ValueError('navigation_routes must contain 1–20 exact routes')
    routes = []
    seen = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {'url', 'local_path'}:
            raise ValueError('Each navigation route requires url and local_path only')
        url, path = item['url'], item['local_path']
        if not isinstance(url, str) or not url or url != url.strip() or any(c.isspace() for c in url) or any(c in url for c in '*\\'):
            raise ValueError('Navigation URL must be exact HTTP(S), without wildcards')
        try:
            parsed = urlsplit(url)
            good = parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username and not parsed.password and not parsed.fragment
            parsed.port
        except ValueError:
            good = False
        if not good or url in seen:
            raise ValueError('Navigation URLs must be unique exact HTTP(S) addresses')
        if (not isinstance(path, str) or not path.startswith('/') or path.startswith('//')
                or any(c in path for c in '?#+\\') or any(c.isspace() for c in path)
                or '..' in unquote(path).split('/') or urlsplit(path).netloc):
            raise ValueError('Navigation local_path must be an absolute local file path')
        seen.add(url)
        routes.append({'url':url, 'local_path':path})
    return routes


# Served URL of a task whose site no longer names its captured host: pet-09's pages and instruction
# say norwegianforestcattery.com, so the URL bar does too. provenance.json keeps the captured URL.
SERVED_URL = {'https://norwegianforestcattery.company.com/about-our-cattery.html': 'https://norwegianforestcattery.com/about-our-cattery.html'}


def resolve_source_transport(provenance, evaluation):
    source = provenance['source']
    original = source.get('url', source.get('source_url'))
    adaptation = provenance.get('local_transport')
    if adaptation is None:
        return SERVED_URL.get(original, original), None
    if (not isinstance(adaptation, dict) or set(adaptation) - {'scheme','reason','navigation_routes'}
            or 'reason' not in adaptation or not ({'scheme','navigation_routes'} & set(adaptation))
            or not isinstance(adaptation['reason'], str) or not adaptation['reason'].strip()):
        raise ValueError('local_transport requires a reason and documented scheme or navigation_routes')
    local = original
    if 'scheme' in adaptation:
        if adaptation['scheme'] != 'https':
            raise ValueError('Only documented HTTPS source replay is supported')
        parsed = urlparse(original)
        if parsed.scheme != 'http' or not parsed.hostname or parsed.username or parsed.password or parsed.port is not None:
            raise ValueError('Transport adaptation requires an unported HTTP source URL')
        if any(a.get('type') == 'observed_url' for a in evaluation.get('anchors', [])):
            raise ValueError('URL-evidence tasks must preserve the original source scheme')
        local = parsed._replace(scheme='https').geturl()
    routes = navigation_routes(adaptation['navigation_routes']) if 'navigation_routes' in adaptation else None
    record = {'original_source_url':original, 'local_browser_url':local,
              'reason':adaptation['reason'], 'scope':'same_host_scheme_only' if routes is None else 'exact_navigation_urls_only'}
    if routes is not None:record['navigation_routes'] = routes
    return local, record
