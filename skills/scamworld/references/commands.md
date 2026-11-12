# Commands and options

`<task>` is a task id or the path of a task folder. Every command has `--help`.

| command | what it does | model |
|---|---|---|
| `scamworld tasks [--scene S] [--benign\|--scam]` | list tasks (`SCAMWORLD_TASKS=<folder>` lists another folder) | no |
| `scamworld run <task> --model M --base-url URL` | one episode of the built-in agent | yes |
| `scamworld evaluate <runs>... [--evaluator E]` | outcome of finished episodes | no with `rules` or your function |
| `scamworld table <runs>... [--rows R] [--cols C]` | outcomes counted per model, setting, task or tag | no |
| `scamworld observe <task> [--obs MODES]... [--path NAME[:N]] [--click BID]... [--goto URL] [--grep TEXT] [--out DIR]` | what the agent receives on a page, after a scripted path, clicks or an address | no |
| `scamworld signs <task>` | the task's warning signs and where they are shown | no |
| `scamworld serve <task>` | serve the website on 127.0.0.1 to look at it in a browser | no |
| `scamworld new-task <folder> --from <task> [--instruction T]` | a copy of a task under a new id, with your request | no |
| `scamworld new-task <folder> [--benign] [--url URL]` | a runnable task with a new website from the template | no |
| `scamworld verify <task>` | scripted browser checks of a task | no |
| `scamworld exp plan\|run custom --models ...` | many tasks, models and settings; resumable | yes |
| `scamworld check` | released task files against the release manifest | no |
| `scamworld score <runs>...`, `scamworld judge ...` | recompute the rule score; run the reason judge (docs/evaluators.md) | judge only |

`<runs>` is a run folder or any folder above run folders.

## `scamworld run`

| option | default | meaning |
|---|---|---|
| `--model M` | a model billed through OpenRouter | sent unchanged as the request's `model` with `--base-url`; `endpoint:NAME` reads the entry NAME of `configs/endpoints.json` |
| `--base-url URL` | | any OpenAI-compatible API, e.g. `http://localhost:8000/v1` |
| `--api-key-env VAR` | no key sent | name of the variable that holds the key |
| `--instruction TEXT`, `--instruction-file FILE` | the task's request | your request, for this run only |
| `--evaluate E` | | also print the outcome: `rules`, `scamworld` or `FILE.py:FUNC` |
| `--obs MODES` | `screenshot,ax_controls` | what the agent sees (below) |
| `--actions MODES` | `bid` (`coord` when `--obs` has no element ids) | how the agent acts: `bid`, `coord`, `bid,coord` |
| `--max-steps N` | 60 | actions per episode |
| `--runs N` | 1 | episodes on this task |
| `--tag NAME`, `--out DIR` | `results/sitekit/<task>/pilot/<tag>-<i>/` | the run folder |
| `--judge auto\|v4\|off` | `auto` | the in-episode reason judge; `off` skips it |
| `--max-cost USD` | 5 | stop an episode at this spend |
| `--allow-paid` | off | needed for paid closed models. Only when the user says so |

## What the agent sees: `--obs`

| value | the agent gets |
|---|---|
| `screenshot,ax_controls` (default) | a screenshot and `controls`, the list of the page's elements |
| `screenshot` | the screenshot only; it acts by pixel position |
| `som` | a screenshot with a numbered label on each element |
| `ax_controls` | `controls` only: for a text-only model, and for a quick first check |
| `ax_tree` | the accessibility tree as text (`axtree_txt`) |
| `html` | the pruned page source (`pruned_html`) |

Values combine with commas. The key `screenshot` is in the observation only with `screenshot` or `som`.

## Environment variables

| variable | meaning |
|---|---|
| `SCAMWORLD_TASKS` | the folder of tasks (default `tasks/`); set it to your own folder to use your tasks by id |
| `SCAMWORLD_URL_VISIBILITY=hidden` | removes the page address from what the agent gets |
| `SCAMWORLD_INSTRUCTION_LANG=en` | the English request on non-English websites (default `local`) |
| `SCAMWORLD_SYSTEM_NOTE="..."` | one sentence added to the system prompt |
| `SCAMWORLD_INTERFACE_VARIANT` | `a12` (default: the request is sent once) or `a11` (repeated in every observation) |
| `SCAMWORLD_OFFSITE=allowlist` | lets the agent open 8 real hosts (needs network); only when the user asks |
| `SCAMWORLD_CHROME_PATH` | the Chrome or Chromium executable |
| `SCAMWORLD_ENDPOINTS` | the endpoints file for `--model endpoint:NAME` (default `configs/endpoints.json`, which you create from `configs/endpoints.example.json`) |
| `SCAMWORLD_JUDGE_ENDPOINT`, `SCAMWORLD_JUDGE_MODEL`, `SCAMWORLD_JUDGE_API_KEY_ENV` | the API of the reason judge (docs/model-apis.md) |

Set `SCAMWORLD_TASKS` before the first import of `scamworld` in Python.

## Python

```python
from scamworld.gym import ScamWorldEnv, Agent, run_episode
from scamworld import evaluators                # evaluators.evaluate(run_dir, 'rules' or 'my_eval.py:evaluate')
from scamworld.corpus import index              # index()['tasks'] lists the task rows
```

`run_episode(task, agent, out_dir=None, max_steps=None, evaluator=None, instruction=None, obs_modes=..., action_modes=...)`
runs one episode of an object with `reset(goal, system_prompt)` and `act(obs)`, and returns the evaluator's dict with
`run_dir`.

`ScamWorldEnv(task, out_dir=None, max_steps=None, headless=True, obs_modes='screenshot,ax_controls', action_modes=None, instruction=None)`:
`reset()`, then `step(action)` until `terminated or truncated`; `evaluate('rules')` saves the run folder and scores it;
`close()`. `env.system_prompt()` is the full action protocol.

An action is one JSON object: `click` / `hover` (`bid`), `fill` (`bid`, `text`), `select` (`bid`, `label`), `press`
(`key`), `scroll` (`dy`), `goto` (`url`), `back`, `forward`, `new_tab`, `tab_close`, `tab_focus` (`index`), `wait`
(`ms`), `finish` (`message`). The observation has `goal`, `url`, `last_action_error` and the fields of the `--obs`
setting. Reference: docs/api.md, docs/custom-agents.md.
