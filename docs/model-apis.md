# Tutorial 3: your own model API

The built-in agent (`scamworld run`) runs on any server that speaks the OpenAI chat-completions API: vLLM, SGLang,
Ollama, LM Studio, llama.cpp server, LiteLLM, Together, Fireworks, OpenAI, OpenRouter, ... There is no model allowlist,
no price table to fill in and no budget ledger to set up for these endpoints.

## One flag

```bash
uv run scamworld run prize-07 --model Qwen/Qwen3-VL-8B-Instruct --base-url http://localhost:8000/v1
uv run scamworld run prize-07 --model gpt-4.1-mini --base-url https://api.openai.com/v1 --api-key-env OPENAI_API_KEY
```

- `--model` is sent as the request's `model` field, unchanged.
- `--api-key-env` names the environment variable that holds the key (sent only in the `Authorization: Bearer` header).
  Without it no key is sent, which is what local servers expect.
- `--max-steps` (default 60) and `--max-cost` (USD per episode, default 5) cap an episode; `--runs N` repeats it;
  `--out DIR` sets the run folder.

Serving a model locally, for example with vLLM:

```bash
vllm serve Qwen/Qwen3-VL-8B-Instruct --max-model-len 32768
uv run scamworld run prize-07 --model Qwen/Qwen3-VL-8B-Instruct --base-url http://localhost:8000/v1
```

## Named endpoints

For settings beyond the URL, describe the endpoint once in `configs/endpoints.json` (template:
[configs/endpoints.example.json](../configs/endpoints.example.json)) and use `--model endpoint:<name>`.
Copy the template first, then edit the copy:

```bash
cp configs/endpoints.example.json configs/endpoints.json
```

```json
{"endpoints": {
  "vllm-qwen-vl": {
    "base_url": "http://localhost:8000/v1",
    "model": "Qwen/Qwen3-VL-8B-Instruct",
    "api_key_env": null,
    "max_tokens": 4096,
    "context": 32768,
    "vision": true,
    "extra_body": {"chat_template_kwargs": {"enable_thinking": false}}
  }
}}
```

```bash
uv run scamworld run prize-07 --model endpoint:vllm-qwen-vl
uv run scamworld run prize-07 --model endpoint:vllm-qwen-vl --endpoints path/to/other-endpoints.json   # or SCAMWORLD_ENDPOINTS
```

| key | meaning |
|---|---|
| `base_url`, `model` | required; `base_url` ends in `/v1` (or is the full `/chat/completions` URL) |
| `api_key_env` | environment variable with the key; `null` for none |
| `max_tokens` | output cap per call (reasoning tokens count against it on most servers); default 16,384 |
| `context` | the model's context length in tokens; caps the accessibility list sent per step (default 128,000) |
| `vision` | `false` for text-only models: screenshots are left out of the request (also pass `--obs ax_controls`) |
| `reasoning_effort` | sent as `reasoning_effort` (`low` / `medium` / `high`) when set |
| `extra_body` | merged into every request last, e.g. `{"chat_template_kwargs": {"enable_thinking": false}}`, `{"top_p": 0.95}` |
| `drop_fields` | request fields your server rejects, e.g. `["response_format"]` |
| `price` | `{"input_per_mtok", "output_per_mtok"}` in USD per million tokens; without it the cost is the server's `usage.cost` if it reports one, else 0 |
| `timeout` | seconds per call (default 300). On `--base-url` and `endpoint:` servers, 408, 409, 425, 429, 500, 502, 503 and 504, timeouts and connection errors are retried after 4, 8 and 16 s. `openai:`, `anthropic:` and `google:` (a fixed 300 s per call) resend 408, 429 (except a 429 that says the quota or balance is gone; Google's is always resent), 5xx, timeouts and connection errors after the same waits, or after the server's Retry-After when it is longer (at most 60 s) |

## What the model receives

The same request every other backbone gets: a system message with the action protocol, the user's request and saved
details once, then per step a user message with the observation as JSON (`url`, the accessibility `controls`,
`last_action_error`) and the screenshot as a base64 PNG `image_url` part; `temperature` 0; `max_tokens`. Fields that only
OpenRouter understands (`reasoning`, `provider`, `usage`) are not sent. The model answers with optional notes followed by
one JSON action, e.g.

```
The confirmation dialog asks for the card PIN and a one-time code. A delivery company never needs those.
{"action": "finish", "message": "I did not pay: the payment step asks for your card PIN and the bank's one-time code ..."}
```

Replies in a model's own tool-call markup (several open models write those) are read as the same action when they map onto
exactly one. Every reply, its notes and how it was read are in `choices.json`; `score.json` records `transport: "endpoint"`
and the endpoint (name, base URL, model; never the key).

Text-only model:

```bash
uv run scamworld run prize-07 --model endpoint:ollama-text --obs ax_controls
```

## The reason judge on your own API

The default evaluator classifies why an agent stopped with an LLM (docs/evaluators.md). Point it at an endpoint too:

```bash
export SCAMWORLD_JUDGE_ENDPOINT=vllm-judge          # a name in the endpoints file
# or: export SCAMWORLD_JUDGE_ENDPOINT=http://localhost:8001/v1 SCAMWORLD_JUDGE_MODEL=Qwen/Qwen3-32B
uv run scamworld evaluate results/sitekit/prize-07/pilot
uv run scamworld judge --runs results/sitekit/prize-07/pilot --backend endpoint --judge-endpoint vllm-judge --write
```

Without `SCAMWORLD_JUDGE_ENDPOINT` the judge uses OpenRouter, with the key from `.env.openweights` or, when that file
does not exist, from `.env`; `--backend endpoint|openrouter` chooses explicitly. `.env.openweights` (path in
`SCAMWORLD_OPENWEIGHTS_ENV_FILE`) is an optional second key file with an `OPENROUTER_API_KEY`, for the judge and for the
open-weight OpenRouter agent models (`google/gemma`, `qwen/`, `z-ai/`, `deepseek/`, `meta-llama/`, `mistralai/` ids);
without it `.env` serves both, so one key file is enough.

Judge settings read from the environment:

| variable | meaning |
|---|---|
| `SCAMWORLD_JUDGE_ENDPOINT` | the judge API: a name in the endpoints file, or a base URL (then `SCAMWORLD_JUDGE_MODEL` is required). When set and no backend is chosen, the backend is `endpoint` |
| `SCAMWORLD_JUDGE_MODEL` | the judge model id, used when `SCAMWORLD_JUDGE_ENDPOINT` is a URL |
| `SCAMWORLD_JUDGE_API_KEY_ENV` | the name of the variable that holds the key for a URL endpoint; unset means no key is sent. A named endpoint uses its own `api_key_env` |
| `SCAMWORLD_JUDGE_BACKEND` | `endpoint` or `openrouter`: the backend of the default `scamworld` evaluator (`scamworld evaluate`) when `judge_backend` is not given in `--options`. Unset: `endpoint` if `SCAMWORLD_JUDGE_ENDPOINT` is set, else `openrouter` when a key is configured. `scamworld judge` ignores it; use `--backend` |

## Docker

Inside the container `localhost` is the container itself. For a server on the host use `--network host` (Linux), or
`host.docker.internal` (macOS, Windows):

```bash
docker run --rm --network host -v "$PWD/results:/runs" wuyoscar666/scamworld:1.2 \
  run prize-07 --model Qwen/Qwen3-VL-8B-Instruct --base-url http://localhost:8000/v1
docker run --rm -e OPENAI_API_KEY -v "$PWD/results:/runs" -v "$PWD/configs/endpoints.json:/config/endpoints.json:ro" \
  -e SCAMWORLD_ENDPOINTS=/config/endpoints.json wuyoscar666/scamworld:1.2 run prize-07 --model endpoint:openai
```

## Other built-in backends

- OpenRouter ids (`vendor/model`) with the key in `.env` (`OPENROUTER_API_KEY`): only the 12 ids in `AUTHORIZED_MODELS`
  (`src/scamworld/agents/openrouter.py`) run this way: `google/gemma-4-31b-it`, `google/gemini-3.8-flash`,
  `anthropic/claude-haiku-5.5`, `anthropic/claude-sonnet-5.5`, `openai/gpt-5.6-luna`, `openai/gpt-5.6-terra`,
  `qwen/qwen3.8-flash`, `z-ai/glm-5.3-flash`, `deepseek/deepseek-v4.1-flash`, `deepseek/deepseek-v4.1-flash-1017`,
  `x-ai/grok-4.7` and `moonshotai/kimi-k3`. All are billed to your key. `scamworld run` refuses ids that contain `gemini`,
  `openai/`, `anthropic/` or `x-ai/` unless you pass `--allow-paid`. For any other OpenRouter model use the endpoint route
  above (`--base-url https://openrouter.ai/api/v1 --api-key-env OPENROUTER_API_KEY`).
- `openai:<id>`, `anthropic:<id>`, `google:<id>` call the vendors' own APIs (`SCAMWORLD_DIRECT_ENV` names a dotenv file
  with `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY`), with prices from `configs/direct-prices.json`. They are
  billed to your account with the vendor, and `scamworld run` refuses them without `--allow-paid`; the refusal names the
  billing route (the vendor's own API for these ids, OpenRouter for the OpenRouter ids above). `--base-url` and `endpoint:`
  need no `--allow-paid`.
- `--allow-paid` gates `scamworld run` only. `scamworld exp` has no such flag: a plan runs the models it lists, paid ones
  included, and `--budget` (USD, default 10 per invocation) bounds the spending: no new episode starts once the cost
  reported by finished episodes reaches it, and the episodes already running finish. An episode whose cost is unknown also
  stops the dispatch (except on the free gateway, `cz/` ids). Estimates in `scamworld exp plan` are 0 for the free gateway
  models (`cz/` ids).
- Before it dispatches anything, `scamworld exp run` checks the plan: every model id can run (OpenRouter ids must be in
  `AUTHORIZED_MODELS`; `cz/` ids need the model gateway's key, which is not public), the key file each model uses holds a
  key, and the judge key is there when the plan keeps the in-episode judge on. Each problem is one line and nothing is
  dispatched; `scamworld exp plan` prints the same problems as notes. A plan with a fixed list of released tasks
  that the checkout does not have (`smoke` and `obs-smoke`) stops with `<plan>: its tasks are not in this
  checkout (missing <file>): download the full task set (the Hugging Face dataset) or use the Docker image`; a
  plan that needs an input this release does not contain stops with `<plan> needs <the input, e.g. the obs-60 task
  list> (not part of this release)`.
- Whatever fails before an episode's first model call (the task or evaluator, a missing key, a model id that cannot run, the
  judge's key when the judge is on, the browser, the first page) is a setup failure: the `score.json` that `scamworld exp`
  writes for it has stop `infra_error`, `infra_stage` `setup`, `cost_known` true and cost 0, and it never blocks a later
  run of the episode. During `scamworld exp run` the first setup failure of each model is printed once to stderr, and
  the command ends with one line (`<plan>: N episodes dispatched, N setup failures, N other infrastructure errors`)
  and exits 1 when every dispatched episode failed at setup. `scamworld run` removes the run folder after a setup
  failure when the folder holds no result. `scamworld run --judge v4` with no OpenRouter key for the judge exits with
  one line before the episode starts.
- An attempt whose billing is unknown (a crash or timeout after a paid call) is never replayed automatically. The refusal
  names its folder: check the provider's activity log for that call, then delete the folder to run it again.
- The default model `google/gemma-4-31b-it` and the OpenRouter judge model `deepseek/deepseek-v4.1-flash` are called through
  OpenRouter like the other OpenRouter ids and billed to your key. `SCAMWORLD_BUDGET_LEDGER` and `SCAMWORLD_BUDGET_POLICY`
  (a spend ledger and its policy file, both needed together; a budget policy file is not part of this release) are
  optional, and with `SCAMWORLD_BUDGET_REQUIRED=1` these two models refuse to run without them.

Settings of these backends read from the environment (the key files of the judge are in the section above):

| variable | meaning |
|---|---|
| `SCAMWORLD_OR_ENV` | the dotenv file with `OPENROUTER_API_KEY` that the OpenRouter agent reads, and that an `LLMJudge` created without an `env_file` reads; read when `scamworld` loads. Default: the file of `SCAMWORLD_ENV_FILE`, else `.env`. `scamworld run` and `scamworld exp` never read it for the open-weight ids (`google/gemma`, the default model among them, `qwen/`, `z-ai/`, `deepseek/`, `meta-llama/`, `mistralai/`): they use the file of `SCAMWORLD_OPENWEIGHTS_ENV_FILE` (default `.env.openweights`), or the file of `SCAMWORLD_ENV_FILE` (else `.env`) when that file does not exist |
| `SCAMWORLD_DIRECT_LEDGER` | the file of the spend ledger of the `openai:`, `anthropic:` and `google:` calls. Default: a new file under `results/runs/_ledgers/direct/` for each episode. A ledger file keeps the limit it was created with, and opening it with another one is an error |
| `SCAMWORLD_DIRECT_LIMIT` | the cap of that ledger in USD (default 10, at most 25). Each call reserves its highest possible price before it is sent and is refused when the ledger cannot cover it; the `--max-cost` cap of an episode (5 USD by default) stops it first |

`configs/agent-models.json` holds the model profiles of the paper's runs; profile `r8` has their request settings (reasoning
effort, token limits). Entries named `cz/...` point to a private gateway and cannot be used outside it. Pass `--model` and
`--base-url` for your own model instead.

Your own agent loop needs none of this: see docs/custom-agents.md and `examples/agents/openai_compatible_agent.py`.
