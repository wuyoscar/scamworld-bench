"""Any OpenAI-compatible chat-completions API as the agent's (or the judge's) model: bring your own model.

An endpoint is a server that answers POST <base_url>/chat/completions in the OpenAI format: vLLM, SGLang, Ollama, LM Studio,
llama.cpp server, LiteLLM, Together, Fireworks, OpenAI itself, OpenRouter, ... Its model id is free (no allowlist), its price is
optional (no price: the cost the server reports in usage.cost, else 0), and its calls never touch the OpenRouter budget ledger. Two ways to name one:

  scamworld run shop-01 --model Qwen/Qwen3-VL-8B-Instruct --base-url http://localhost:8000/v1
  scamworld run shop-01 --model endpoint:local-qwen          (an entry of the endpoints file)

Endpoints file: --endpoints FILE, else SCAMWORLD_ENDPOINTS, else configs/endpoints.json (configs/endpoints.example.json shows
every key):

  {"endpoints": {"local-qwen": {"base_url": "http://localhost:8000/v1", "model": "Qwen/Qwen3-VL-8B-Instruct",
                                "api_key_env": null, "max_tokens": 4096, "context": 32768, "vision": true,
                                "price": {"input_per_mtok": 0.0, "output_per_mtok": 0.0},
                                "reasoning_effort": null, "extra_body": {}, "drop_fields": [], "timeout": 300}}}

The request is the one every other backbone gets (same messages, screenshots, temperature 0, max_tokens), minus the OpenRouter-
only fields (`reasoning`, `provider`, `usage`); `reasoning_effort` is sent only when the endpoint sets it, and `extra_body` is
merged last (e.g. {"chat_template_kwargs": {"enable_thinking": false}} for vLLM). The key is read from the environment variable
`api_key_env` (none: no Authorization header), and is only ever sent in that header.
"""
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from scamworld.paths import CONFIGS

PREFIX = 'endpoint:'
ENV = 'SCAMWORLD_ENDPOINTS'
DEFAULT_FILE = CONFIGS / 'endpoints.json'
OPENROUTER_ONLY = ('reasoning', 'provider', 'usage')
RETRY_STATUS = (408, 409, 425, 429, 500, 502, 503, 504)
RETRY_WAIT = (4, 8, 16)


class EndpointError(ValueError):
    pass


class EndpointReplyError(EndpointError):
    """The server answered, but not with a chat completion (not JSON, or no choices): episode error origin provider_response_format."""


@dataclass
class Endpoint:
    base_url: str
    model: str
    name: str = ''
    api_key_env: str | None = None
    max_tokens: int | None = None
    context: int | None = None
    vision: bool = True
    price: dict = field(default_factory=dict)        # USD per million tokens: input_per_mtok, output_per_mtok
    reasoning_effort: str | None = None
    extra_body: dict = field(default_factory=dict)
    drop_fields: list = field(default_factory=list)  # request fields the server rejects (e.g. response_format)
    timeout: float = 300

    def __post_init__(self):
        if not isinstance(self.base_url, str) or not self.base_url.startswith(('http://', 'https://')):
            raise EndpointError('endpoint base_url must be an http(s) URL, e.g. http://localhost:8000/v1')
        if not isinstance(self.model, str) or not self.model.strip():
            raise EndpointError('endpoint model id is required')
        self.base_url = self.base_url.rstrip('/')
        self.name = self.name or self.model

    @property
    def url(self):
        return self.base_url if self.base_url.endswith('/chat/completions') else self.base_url + '/chat/completions'

    def key(self):
        """The API key from the environment variable api_key_env ('' when the endpoint needs none)."""
        if not self.api_key_env:
            return ''
        value = (os.environ.get(self.api_key_env) or '').strip()
        if not value:
            raise EndpointError(f'endpoint {self.name!r}: environment variable {self.api_key_env} is empty')
        return value

    def cost(self, usage):
        """(USD, price_basis) of one call from its usage and the configured price; no price: 0.0, 'unpriced'."""
        usage = usage if isinstance(usage, dict) else {}
        if not self.price:
            return 0.0, 'unpriced'
        n = lambda v: v if isinstance(v, (int, float)) and not isinstance(v, bool) else 0
        usd = (n(usage.get('prompt_tokens')) * float(self.price.get('input_per_mtok') or 0)
               + n(usage.get('completion_tokens')) * float(self.price.get('output_per_mtok') or 0)) / 1e6
        return round(usd, 8), 'endpoint_price'

    def record(self):
        """What score.json keeps about the endpoint (never the key)."""
        return {'name': self.name, 'base_url': self.base_url, 'model': self.model,
                **({'price': self.price} if self.price else {}), **({'extra_body': self.extra_body} if self.extra_body else {})}


def load(path=None):
    """{name: Endpoint} from an endpoints file (missing file: {})."""
    path = Path(path or os.environ.get(ENV) or DEFAULT_FILE)
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding='utf-8'))
    entries = doc.get('endpoints', doc) if isinstance(doc, dict) else None
    if not isinstance(entries, dict):
        raise EndpointError(f'{path}: expected {{"endpoints": {{name: {{base_url, model, ...}}}}}}')
    out = {}
    for name, entry in entries.items():
        if name.startswith('_'):
            continue
        try:
            out[name] = Endpoint(name=name, **{k: v for k, v in entry.items() if not k.startswith('_')})   # _keys: comments
        except TypeError as error:
            raise EndpointError(f'{path}: endpoint {name!r}: {error}') from error
    return out


def is_endpoint(model):
    return isinstance(model, str) and model.startswith(PREFIX)


def resolve(model, base_url=None, api_key_env=None, endpoints=None):
    """The Endpoint for an agent model argument, or None for the built-in backends (OpenRouter ids, cz/, openai:, ...).
    `endpoint:<name>` reads the endpoints file; any model id with base_url is an ad-hoc endpoint."""
    if is_endpoint(model):
        name = model[len(PREFIX):]
        where = endpoints or os.environ.get(ENV) or DEFAULT_FILE
        if not Path(where).is_file():
            raise EndpointError(f'endpoints file {where} not found (needed for endpoint {name!r}): copy configs/endpoints.example.json '
                                f'to configs/endpoints.json and edit it, or set {ENV} to your file (scamworld run also takes --endpoints FILE)')
        table = load(endpoints)
        if name not in table:
            raise EndpointError(f'no endpoint {name!r} in {where} (defined: {", ".join(sorted(table)) or "none"})')
        return table[name]
    if base_url:
        return Endpoint(base_url=base_url, model=model, api_key_env=api_key_env)
    return None


def _strip_images(messages):
    out = []
    for m in messages:
        content = m.get('content')
        if isinstance(content, list):
            m = {**m, 'content': [part for part in content if part.get('type') != 'image_url']}
        out.append(m)
    return out


class EndpointLedger:
    """What score.json `budget_state` records for an endpoint run: the spend of this episode's calls (no shared ledger)."""
    policy_sha256 = None

    def __init__(self):
        self.calls, self.spent = [], 0.0

    def snapshot(self):
        return {'scope': 'endpoint', 'spent_microusd': round(self.spent * 1e6), 'held_microusd': 0, 'calls': list(self.calls)}


class EndpointTransport:
    """complete(body, key) -> (response, sent body, receipt), the call shape of the budget transport, for an Endpoint.
    usage.cost is set from the endpoint's price; without one, from the server's usage.cost if it reports one, else 0, so cost
    accounting downstream is the same for every model."""

    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.key = endpoint.key()
        self.ledger = EndpointLedger()

    def body(self, body):
        e = self.endpoint
        b = {k: v for k, v in body.items() if k not in OPENROUTER_ONLY and k not in e.drop_fields}
        b['model'] = e.model
        if e.max_tokens:
            b['max_tokens'] = e.max_tokens
        if e.reasoning_effort:
            b['reasoning_effort'] = e.reasoning_effort
        if not e.vision:
            b['messages'] = _strip_images(b.get('messages') or [])
        b.update(json.loads(json.dumps(e.extra_body)))
        return b

    def complete(self, body, key=None, caller=None, **_):
        b = self.body(body)
        headers = {'Content-Type': 'application/json'}
        if self.key:
            headers['Authorization'] = 'Bearer ' + self.key
        data = json.dumps(b).encode()
        for attempt in range(len(RETRY_WAIT) + 1):
            try:
                with urllib.request.urlopen(urllib.request.Request(self.endpoint.url, data=data, headers=headers),
                                            timeout=self.endpoint.timeout) as stream:
                    raw = stream.read()
                    try:
                        response = json.loads(raw)
                    except ValueError as error:   # JSONDecodeError, UnicodeDecodeError
                        raise EndpointReplyError(f'endpoint reply is not JSON ({type(error).__name__}: {error}); it starts: '
                                                 f'{raw[:300].decode("utf-8", "replace")!r}') from error
                break
            except urllib.error.HTTPError as error:
                if error.code not in RETRY_STATUS or attempt == len(RETRY_WAIT):
                    raise
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if attempt == len(RETRY_WAIT):
                    raise
            time.sleep(RETRY_WAIT[attempt])
        if not isinstance(response, dict) or not response.get('choices'):
            raise EndpointReplyError('endpoint reply has no choices: ' + json.dumps(response)[:300])
        usage = response.get('usage') if isinstance(response.get('usage'), dict) else {}
        reported = usage.get('cost')
        if not self.endpoint.price and isinstance(reported, (int, float)) and not isinstance(reported, bool) and reported >= 0:
            cost, basis = float(reported), 'provider_reported'   # e.g. OpenRouter's usage.cost
        else:
            cost, basis = self.endpoint.cost(usage)
        response['usage'] = {**usage, 'cost': cost}
        response.setdefault('provider', 'endpoint:' + self.endpoint.name)
        receipt = {'endpoint': self.endpoint.name, 'cost_usd': cost, 'price_basis': basis, 'caller': caller}
        self.ledger.spent += cost
        self.ledger.calls.append(receipt)
        return response, b, receipt
