# Install

Two ways. Docker needs nothing else and has all 430 tasks. A source checkout is what you want for Python code of your own
(an agent, a script) and for looking at a website in your browser.

## Docker

```bash
docker pull wuyoscar666/scamworld:1.2
docker run --rm wuyoscar666/scamworld:1.2 tasks --scene shop
```

Every `scamworld <command>` of this skill is then:

```bash
docker run --rm -v "$PWD/results:/runs" wuyoscar666/scamworld:1.2 <command>
```

| you need | add |
|---|---|
| the run folders on your machine | `-v "$PWD/results:/runs"` (inside the image, `results/` is `/runs`: write `/runs/sitekit/...` in `evaluate` and `table`) |
| a model server on the host | Linux: `--network host`. macOS, Windows: `--base-url http://host.docker.internal:<port>/v1` |
| a key | `-e MY_KEY` and `--api-key-env MY_KEY` |
| task folders of your own | `-v "$PWD/my-tasks:/my-tasks"` and the path `/my-tasks/<id>`; `-e SCAMWORLD_TASKS=/my-tasks` to use them by id |
| files written as you, not root (Linux, `new-task`) | `--user "$(id -u):$(id -g)"` |
| an evaluator file or a request file of your own | `-v "$PWD:/work"` and the path `/work/my_eval.py:evaluate` |
| a Python script (your own agent, the files in `examples/`) | `--entrypoint python -v "$PWD:/work" -w /work`, then `my_agent.py` in place of the command |

`scamworld serve` prints an address inside the container: to look at a website in your browser, use a source checkout.

## From source

Python 3.12 and [uv](https://docs.astral.sh/uv/). `scamworld <command>` is `uv run scamworld <command>`.

```bash
git clone https://github.com/wuyoscar/scamworld-bench && cd scamworld-bench
uv sync
uv run playwright install chromium
uv run scamworld tasks                    # 20 sample tasks
```

On Linux the browser also needs system libraries: `uv run playwright install --with-deps chromium` installs them with
sudo, so tell the user first.

All 430 tasks (about 1.5 GB: tell the user the size and wait for a yes):

```bash
uvx --from huggingface_hub hf download oscarwu/ScamWorld --repo-type dataset --local-dir . --include "tasks/*"
uvx --from huggingface_hub hf download oscarwu/ScamWorld --repo-type dataset --local-dir . --include "release/*"
uv run scamworld check
```

## Check it, without a model

```bash
uv run python examples/agents/scripted_agent.py examples/tasks/parcel-fee-01     # source: prints 'outcome': 'deceived'
scamworld verify prize-07                                                        # Docker or source; last line PASS
```

`verify` replays scripted paths in a real browser and takes 1 to 3 minutes: give it a long timeout. If the browser does
not start, see `troubleshooting.md`.
