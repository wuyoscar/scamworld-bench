# ScamWorld: notes for coding agents

This file is for a coding agent (Claude Code, Codex CLI, Cursor, OpenCode, ...) working in this repository. It is the
one-page map. To set ScamWorld up from nothing, follow [docs/install.md](docs/install.md). The step-by-step recipes are in
the skill, [skills/scamworld/SKILL.md](skills/scamworld/SKILL.md): read that before you do a task for the user.

## What this is

ScamWorld is an interactive environment for evaluating web agents against online fraud. A task is one folder: a website
(`site/`), an ordinary user request (`task.json`) and hidden scoring files (`scoring/`). The agent under test works on the
website in a real browser; the website records what it did (a payment, a submitted password), and the agent ends with a
final message. Each episode leaves a run folder with `trace.json`, `choices.json` and `score.json`. An evaluator is a
function that reads one run folder and returns an outcome.

There are 430 released tasks: 377 on 363 scam websites and 53 on legitimate controls. A clone holds 20 sample tasks; the Docker image
`wuyoscar666/scamworld:1.2` holds all of them. The released requests are one set: the request, the scoring, what the agent
sees, the model, the agent and the website can all be replaced.

## Set up

[docs/install.md](docs/install.md) is the guide: install, a check without a model, the skill, what to report. In short:

```bash
uv sync && uv run playwright install chromium        # Python 3.12 and uv; Linux: docs/install.md, section 1
uv run scamworld tasks                                # lists the tasks; ok-* are legitimate controls
```

With Docker instead: `docker run --rm wuyoscar666/scamworld:1.2 tasks`
([skills/scamworld/references/install.md](skills/scamworld/references/install.md) has the mounts).

## The interfaces

| command | what it does | needs a model |
|---|---|---|
| `scamworld run <task> --model M --base-url URL [--api-key-env VAR]` | one episode of the built-in agent; prints one JSON line with `run_dir` | yes |
| `... --instruction "TEXT"` | the same task with your request in place of the released one | |
| `... --evaluate rules` or `--evaluate my_eval.py:evaluate` | also prints the outcome, from the built-in rules or from your function | |
| `... --obs MODES --actions MODES` | what the agent sees (`screenshot`, `som`, `ax_controls`, `ax_tree`, `html`) and how it acts | |
| `scamworld evaluate <runs> --evaluator E` | outcome of episodes that already ran | no |
| `scamworld table <runs>` | outcomes counted per model, observation setting, task or tag | no |
| `scamworld observe <task> --obs MODES` | what the agent receives on a page | no |
| `scamworld signs <task>` | the task's warning signs and where they are shown (hidden scoring information) | no |
| `scamworld new-task <folder> --from <task> --instruction "TEXT"` | a copy of a task with your request, as a folder you can edit | no |
| `scamworld new-task <folder> --url URL` | a new website from the template | no |
| `scamworld verify <task>` | scripted browser checks of a task; the last line is PASS or FAIL | no |
| `scamworld exp plan\|run custom --models ... --cases ...` | many tasks, models and settings; resumable | yes |

`<task>` is a task id or the path of a task folder. The model is any OpenAI-compatible chat API (vLLM, Ollama, LiteLLM, a
hosted API). In Python: `from scamworld.gym import ScamWorldEnv, Agent, run_episode` gives a `reset` / `step` loop for an
agent of your own. Every command has `--help`; [docs/api.md](docs/api.md) is the reference.

## To run an experiment

1. Ask the user for the model id, its base URL and, if the server needs a key, the name of the environment variable that
   holds it. Do not pick a model for them.
2. Run one short episode to see that it works: `uv run scamworld run shop-11 --model M --base-url URL --max-steps 15 --evaluate rules --judge off`.
3. Read the run folder named by `run_dir`: `trace.json` (every step and site event) and `choices.json` (every model reply).
4. Change what the user wants changed (request, scoring, observation, tasks, models), then scale up with more tasks or
   with `scamworld exp`. `scamworld table <runs>` puts the outcomes side by side.

## Rules

- Never print or write a key. Never run without `--model` (the default model is billed) and never add `--allow-paid` unless the user says so. Pass `--judge off` unless the user wants the reason judge: with an OpenRouter key in `.env.openweights` or `.env`, `scamworld run` calls it on that key.
- Never edit `tasks/`: copy a task with `new-task --from` and edit the copy. After every change to a task folder, run `scamworld verify <folder>` until it prints PASS.
- In an errand, do not tell the agent under test that the website might be a scam. No page of a website may say that it is a test, a demo or part of ScamWorld.
- The websites are reconstructions of reported scams, for research: serve them on 127.0.0.1 only, do not deploy them, do not contact anyone named on them.
- Start with one episode. Ask before a long or parallel batch.
- Say what an agent did only after reading its `trace.json`.

## Where things are

| path | content |
|---|---|
| `skills/scamworld/` | the skill: `SKILL.md`, and `references/` with install, recipes, commands, evaluator, task folder, troubleshooting |
| `docs/install.md` | set-up and update, written for the agent that does it |
| `docs/start-here.md` | the same route as a walk-through for people, with the output of every command |
| `docs/` | `custom-tasks.md`, `custom-agents.md`, `model-apis.md`, `evaluators.md`, `api.md`, `task-format.md` |
| `examples/` | `agents/` (a complete agent on any OpenAI-compatible API), `evaluators/`, `ask-directly/`, `long-requests/` |
| `tasks/` | the released tasks (read-only); `tasks/index.json` lists them |
| `src/scamworld/` | the package |
| `results/` | run folders (created by the commands) |
