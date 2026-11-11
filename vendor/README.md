# vendor/

Third-party sources installed as local packages by `uv sync`, at the commits the paper runs used. Files are
`git ls-files` of the upstream subtree plus LICENSE, byte-identical to the upstream subtree at the pinned commit.

| folder | upstream | commit | subtree |
|---|---|---|---|
| agentlab/ | https://github.com/ServiceNow/AgentLab | 8488c564eea0525aaff5dea189bb03a9b529546e | src/ |
| browsergym-experiments/ | https://github.com/ServiceNow/BrowserGym | e71419aef5759a11cb7896a26c36e5f7e92d82b2 | browsergym/experiments/src/ |

Only `pyproject.toml` here is ours: it declares no dependencies, because the scamworld project pins them.
