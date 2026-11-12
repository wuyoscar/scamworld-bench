# Commands and options

`<task>` is a task id or the path of a task folder.

| command | what it does |
|---|---|
| `scamworld tasks [--scene S] [--benign\|--scam]` | list tasks (`SCAMWORLD_TASKS=<folder>` lists another folder) |
| `scamworld serve <task>` | serve the website on 127.0.0.1 to look at it in a browser |
| `scamworld new-task <folder> [--benign] [--url URL]` | a runnable task from the template |
| `scamworld new-task <folder> --from <task>` | a copy of a task under a new id |
| `scamworld verify <task>` | scripted browser probes, no model |
| `scamworld run <task> --model M [--base-url URL]` | one episode of the built-in agent |
| `scamworld evaluate <run dir>... [--evaluator E]` | outcome of finished episodes |
| `scamworld score <run dir>...` | recompute the rule score from the trace |
| `scamworld judge --runs <run dir>... [--write]` | run the reason judge on finished episodes |
| `scamworld check` | task files against the release manifest (released tasks only) |
| `scamworld exp plan\|run <name>` | the paper's experiment plans over many tasks (docs/custom-tasks.md section B for a plan of your own) |

## `scamworld run`

| option | default | meaning |
|---|---|---|
| `--model M` | `google/gemma-4-31b-it` through OpenRouter (billed) | sent as the request's `model` unchanged with `--base-url`; `endpoint:NAME` reads the entry NAME of `configs/endpoints.json` (copy `configs/endpoints.example.json`) |
| `--base-url URL` | | any OpenAI-compatible API, e.g. `http://localhost:8000/v1` |
| `--api-key-env VAR` | no key sent | name of the variable that holds the key |
| `--max-steps N` | 60 | actions per episode |
| `--runs N` | 1 | episodes on this task |
| `--max-cost USD` | 5 | stop an episode at this spend |
| `--obs`, `--actions` | `screenshot,ax_controls`, `bid` | what the agent sees and does (SKILL.md step 7) |
| `--judge auto\|v4\|off` | `auto` | in-episode reason judge; `off` skips it |
| `--out DIR`, `--tag NAME` | `results/sitekit/<task>/pilot/<tag>-<i>/` | run folder |
| `--allow-paid` | off | needed for `openai:`, `anthropic:`, `google:` ids and for OpenRouter ids that contain `gemini`, `openai/`, `anthropic/`, `x-ai/`. Only when the user says so |

When the model server fails, `scamworld run` prints a note to stderr and the stop is `infra_error`. Check the server, the model id and the base URL (the URL usually ends in `/v1`).

## Environment variables

| variable | meaning |
|---|---|
| `SCAMWORLD_TASKS` | the folder of tasks (default `tasks/`); set it to your own folder to run and score your tasks by id |
| `SCAMWORLD_CHROME_PATH` | the Chrome or Chromium executable (default: Google Chrome on macOS if installed, else Playwright's Chromium) |
| `SCAMWORLD_INTERFACE_VARIANT` | `a12` (default: the request is sent once) or `a11` (repeated in every observation) |
| `SCAMWORLD_URL_VISIBILITY` | `hidden` removes the page address from the observation |
| `SCAMWORLD_INSTRUCTION_LANG` | `local` (default) or `en` |
| `SCAMWORLD_OFFSITE` | `off` (default) or `allowlist` |
| `SCAMWORLD_SYSTEM_NOTE` | a sentence added to the system prompt |
| `SCAMWORLD_ENDPOINTS` | the endpoints file for `--model endpoint:NAME` (default `configs/endpoints.json`, which you create from `configs/endpoints.example.json`) |
| `SCAMWORLD_JUDGE_ENDPOINT`, `SCAMWORLD_JUDGE_MODEL`, `SCAMWORLD_JUDGE_API_KEY_ENV` | the API of the reason judge (docs/model-apis.md) |

Set `SCAMWORLD_TASKS` before the first import of `scamworld` in Python.

## Python

```python
from scamworld.corpus import index              # index()['tasks'] lists the task rows
from scamworld.gym import ScamWorldEnv, Agent, run_episode
from scamworld import evaluators                # evaluators.evaluate(run_dir, 'rules')
```

`ScamWorldEnv(task, out_dir=None, max_steps=None, headless=True, obs_modes='screenshot,ax_controls', action_modes=None, model_context=None, instruction=None)`; `reset()` then `step(action)` until `terminated or truncated`; `save()` writes the run folder; `evaluate('rules')` scores it; `close()`. An action is one JSON object: `click`/`hover` (`bid`), `fill` (`bid`, `text`), `select` (`bid`, `label`), `press` (`key`), `scroll` (`dy`), `goto` (`url`), `back`, `forward`, `new_tab`, `tab_close`, `tab_focus` (`index`), `wait` (`ms`), `finish` (`message`). `env.system_prompt()` is the full protocol text. Reference: docs/api.md, docs/custom-agents.md.
