"""Browser environment: local site server, BrowserGym task/env, observation and action interface."""


def __getattr__(name):   # lazy: scoring and analysis import this package without starting Playwright
    if name in ('FormalBrowserEnv', 'FormalBrowserTask'):
        from . import environment
        return getattr(environment, name)
    if name in ('BrowserRuntime', 'LocalSiteServer'):
        from . import runtime
        return getattr(runtime, name)
    raise AttributeError(name)


__all__ = ['FormalBrowserEnv', 'FormalBrowserTask', 'BrowserRuntime', 'LocalSiteServer']
