"""Resolve an installed browser without machine-specific requirements on Linux."""
import os, sys
from pathlib import Path

# Network isolation. Requests the browser makes by itself bypass Playwright's route
# handler: the favicon (/favicon.ico or a declared icon) and redirects it follows. Under a logical domain these went to
# the live site. Every Chromium therefore gets a proxy that does not exist, bypassed only for the local site server
# (127.0.0.1): the browser itself reaches no other host, and its DNS lookups for other hosts are not made either.
# route.fetch (Playwright's own HTTP client, not the browser) is not affected.
ISOLATION_ARGS = ['--proxy-server=http://127.0.0.1:9', '--proxy-bypass-list=<-loopback>;127.0.0.1']


def isolated(launch_kwargs):
 """Chromium launch kwargs with ISOLATION_ARGS appended to `args` (a new dict; the caller's is not changed)."""
 return {**launch_kwargs, 'args': list(launch_kwargs.get('args') or []) + ISOLATION_ARGS}


def configure_browser(cache_dir):
 if sys.platform=='darwin':
  from scamworld.env.browsergym_adapter import configure_local_chrome
  configure_local_chrome(cache_dir)
 # Linux uses the Chromium revision installed by this Playwright version.

def chromium_kwargs():
 explicit=os.environ.get('SCAMWORLD_CHROME_PATH')
 if explicit:
  if not Path(explicit).is_file():raise FileNotFoundError('SCAMWORLD_CHROME_PATH is not an executable file')
  return {'executable_path':explicit}
 mac=Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
 return {'executable_path':str(mac)} if sys.platform=='darwin' and mac.is_file() else {}
