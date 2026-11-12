# Set up or update ScamWorld

For the AI doing the work. This one guide covers a first set-up and an update. Run every command yourself, and tell the
user what section 4 says.

ScamWorld is an environment for evaluating web agents against online fraud: rebuilt scam websites, an ordinary user
request, a real browser. You are setting it up so that the user can run agents on it. You are not the agent under test.

## 0. Before you start

- You must be able to run terminal commands. If you cannot, tell the user: "Please allow me to run commands, then ask
  again."
- Already set up? If there is a `scamworld-bench` folder with a `pyproject.toml` here, or the user names one, go to
  [Update](#update).
- Choose the way yourself unless the user has said which. From source is the default: it gives you the skill, the
  examples and a preview of the websites. Use [Docker](#docker) when the user asks for it or Python cannot be installed.
- From source needs `git` and [uv](https://docs.astral.sh/uv/). If `uv --version` fails, ask the user: "May I install
  uv, a small tool that installs Python programs? It needs no admin password." After a yes, install it with a package
  manager the user already has (`brew install uv`, `pipx install uv`). If there is none, use the method in its
  [documentation](https://docs.astral.sh/uv/getting-started/installation/): download the installer to a file and read
  it before you run it, do not pipe a download into a shell. Open a new shell if `uv` is still not found.

## 1. Install

```bash
git clone --depth 1 https://github.com/wuyoscar/scamworld-bench && cd scamworld-bench
uv sync
uv run playwright install chromium
```

On Linux the browser also needs system libraries: `uv run playwright install --with-deps chromium` installs them with
sudo. Tell the user before you run it, and ask them to run it if you have no sudo.

## 2. Check it, without a model

```bash
uv run scamworld tasks > /dev/null                                              # the count stays on screen: 20 tasks
uv run python examples/agents/scripted_agent.py examples/tasks/parcel-fee-01   # the printed dict has 'outcome': 'deceived'
```

The second command serves a website to a headless browser, lets a scripted agent click through the payment, and scores
the episode. If the browser cannot start, your own sandbox is probably blocking it: ask the user to allow this command
to start a browser, and run it again once they agree. Do not go on until it prints `'outcome': 'deceived'`.

## 3. Install the skill for yourself

```bash
mkdir -p .claude/skills .agents/skills
cp -R skills/scamworld .claude/skills/        # Claude Code
cp -R skills/scamworld .agents/skills/        # Codex CLI, Cursor, OpenCode
```

Then read `skills/scamworld/SKILL.md`. It is how you do everything the user asks for next: run a model on a task, give a
website the user's own request or a question, score runs with a function, compare models, show what the agent sees,
make a task or a website. `AGENTS.md` at the top of the repository is the one-page map.

## 4. Report to the user

Tell the user this, filled in, and nothing else:

> ScamWorld is set up in `<folder>`: `<N>` tasks, and the browser check passed.
>
> To run an agent I need the model id and its base URL (any OpenAI-compatible API, for example
> `http://localhost:8000/v1`), and, if the server needs a key, the name of the environment variable that holds it.
>
> Then you can say, for example:
> - "Run shop-11 and tell me what the agent did."
> - "Give the shop this request instead: ..."
> - "Ask it whether the shop is a scam, and score the answer."
> - "Compare two models on the shop tasks."
> - "Show me what the agent sees on the checkout page."
> - "Make a scam website of my own."
> - "Get all 430 tasks." (the clone has 20 samples; the full set is about 1.5 GB)

Do not start a model run before the user has named the model. Never print or store a key.

## Update

```bash
cd scamworld-bench && git pull --ff-only && uv sync
cp -R skills/scamworld .claude/skills/ && cp -R skills/scamworld .agents/skills/
uv run scamworld tasks > /dev/null
```

Tell the user which version is installed (`uv run python -c "import scamworld; print(scamworld.__version__)"`), and read
`skills/scamworld/SKILL.md` again: commands may have been added.

## Docker

```bash
docker pull wuyoscar666/scamworld:1.2
docker run --rm wuyoscar666/scamworld:1.2 tasks > /dev/null             # the count stays on screen: 430 tasks
docker run --rm wuyoscar666/scamworld:1.2 verify prize-07 | tail -1     # PASS, after 1 to 3 minutes
```

The image has the package, all 430 tasks, the browser and the fonts, and no skill. Read the skill online,
<https://raw.githubusercontent.com/wuyoscar/scamworld-bench/main/skills/scamworld/SKILL.md>, and its
`references/install.md` next to it for the mounts each command needs. Then report as in section 4, with "the Docker
image" as the folder.

## Later

- "Get all 430 tasks" (source): download `tasks/*` and `release/*` from the Hub, then check them. It is about 1.5 GB:
  tell the user the size and wait for a yes.
  ```bash
  uvx --from huggingface_hub hf download oscarwu/ScamWorld --repo-type dataset --local-dir . --include "tasks/*"
  uvx --from huggingface_hub hf download oscarwu/ScamWorld --repo-type dataset --local-dir . --include "release/*"
  uv run scamworld check
  ```
- Everything else is in the skill: running, requests, scoring, comparing, tasks and websites of the user's own, and what
  to do when something fails (`references/troubleshooting.md`).
