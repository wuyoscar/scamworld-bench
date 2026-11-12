# When something goes wrong

Read the run folder before guessing: `choices.json` has every model reply and the action read from it, `trace.json` every
step, `score.json` the `stop` reason.

## Install and tasks

| what you see | what it means | what to do |
|---|---|---|
| `scamworld tasks` lists 20 tasks | a clone holds the 20 sample tasks | download the rest (`install.md`, "All 430 tasks") or use the Docker image; then `scamworld check` |
| `verify` ends `FAIL ['crash']`, or no browser starts | Chrome could not start; in a coding agent it is usually the agent's own sandbox | ask the user to allow the command to start a browser, then run it again; on a fresh machine run `uv run playwright install chromium` |
| `verify` ends `FAIL [...]` with probe names | those scripted paths are not scored as intended any more | read the probe lines with `"ok": false`. Usual causes after an edit: the phrase of an anchor (`text_contains`) is no longer on the page, a button lost its `data-dx-do` attribute, or a path in `scoring/spec.json` clicks something that is gone |
| `evaluate` cannot find the task of a run | the run was made on a task outside `tasks/` | set `SCAMWORLD_TASKS` to the folder that holds the task |
| files written by `new-task` in Docker belong to root (Linux) | the container ran as root | add `--user "$(id -u):$(id -g)"` |
| the address printed by `serve` in Docker does not open | it is `127.0.0.1` inside the container | use a source checkout for `serve` |

## Model server

| what you see | what it means | what to do |
|---|---|---|
| `"stop": "infra_error"` | the model server failed, not the agent | the last entry of `choices.json` with an `error` has the status and the body. Check the base URL, the model id and the key variable; from Docker, `localhost` is the container (`install.md`, the row on a model server on the host) |
| `"stop": "max_steps"` | the step limit was reached before the agent finished | raise `--max-steps` (a question that asks the agent to look around needs about 30) |
| `"stop": "protocol_error"` | a model reply was not an action in the required form, for example plain prose | the last entry of `choices.json` has the raw reply. Run the episode again, or use a model that follows the format |
| `"stop": "reasoning_exhausted"` | the model spent its output limit on thinking, twice in one step, before any answer | raise `max_tokens` or switch the thinking off (the row on rejected replies below) |
| `"stop": "provider_refused"` | the model server refused the request (a 403, a content filter) | the last entry of `choices.json` has the status; another model or provider |
| `"stop": "agent_error_or_budget"` | the agent stopped on an error of its own or on its cost limit (`--max-cost`) | the last entry of `choices.json` with an `error` |
| the run asks for an OpenRouter key or refuses a paid model | no `--model` / `--base-url` was given, so the default model (billed through OpenRouter) was chosen | always pass `--model` and `--base-url` |
| the episode ends `truncated` or `no_answer`, and `choices.json` is full of rejected replies | the model's replies hold no JSON action. With a thinking model the reply is often cut off before the answer, because the thinking counts against `max_tokens` | raise `max_tokens` or switch the thinking off: in an endpoint entry (`max_tokens`, `extra_body`, docs/model-apis.md), or for the example agent `OPENAI_MAX_TOKENS` and `OPENAI_EXTRA_BODY='{"chat_template_kwargs": {"enable_thinking": false}}'` |
| every step takes tens of seconds although the model answers fast | the screenshots are slow to upload to the server | for a first check use `--obs ax_controls` (text only); for real runs put the model server on the same network |
| a model call never returns | a dropped connection | the built-in agent gives a call 300 s and retries (`timeout` in an endpoint entry); the example agent gives it 120 s and retries once (`OPENAI_TIMEOUT`) |
| a text-only model fails on the first step | it was sent a screenshot | `--obs ax_controls`, and `"vision": false` in its endpoint entry |

## Results that look wrong

| what you see | what it means | what to do |
|---|---|---|
| `declined` where you expected `detected` | the agent stopped, but its final message did not name the problem. `--evaluator rules` reads the task's keyword rubric; the default evaluator asks a judge model and needs its key | read the final message in `trace.json`; score with your own function if you want another rule (references/evaluator.md) |
| the agent stops and says the price is over the limit | the request's spending limit is below the checkout total | raise the limit in the request, or accept that this request tests the limit, not the scam |
| the agent says a saved card or address is missing | the request says something is saved that the page does not show | keep `variant_of` in a copied task, and write only what the page shows on arrival (SKILL.md rule 4) |
| the first run of a new request ends in two or three steps | the request sends the agent to a page the start page does not link to, or asks for something the site does not have | `scamworld serve <task>` and click the route yourself, then rewrite the request |
