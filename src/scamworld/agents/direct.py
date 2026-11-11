"""Direct transport: the agent calls OpenAI, Anthropic or Google's own API instead of OpenRouter.

Model strings are `openai:<id>`, `anthropic:<id>` and `google:<id>` (any model of the vendor; `vendor/model` ids keep going to
OpenRouter, `cz/...` to the free model gateway, neither is touched here). The agent builds the same OpenRouter-shaped request as ever
(messages with data-URL images, max_tokens, the profile's `reasoning` field); this module turns it into the vendor's request,
sends it, and turns the answer back into the OpenRouter response shape (choices[0].message.content / .reasoning, finish_reason,
usage.prompt_tokens / completion_tokens / completion_tokens_details.reasoning_tokens / cost, provider), so the reply is decoded,
recorded and scored by exactly the code of every other model. Only that normalised shape leaves this module.

What the request carries: the same messages and images, the same max_tokens (output cap, reasoning counted against it) and
reasoning effort `medium`; everything else is the vendor's default. Temperature: the OpenRouter body sends 0 and OpenRouter
forwards a parameter only to a provider that supports it, so Gemini (which takes temperature with thinking on) ran at 0 and gets
0 here; OpenAI's reasoning models and Anthropic with thinking do not take it, so OpenRouter dropped it and so does this module. Keys come from the dotenv file named by SCAMWORLD_DIRECT_ENV (OPENAI_API_KEY,
ANTHROPIC_API_KEY, GEMINI_API_KEY), only ever in a request header, never in a URL, a log or a record.

    openai     POST /v1/chat/completions   Authorization: Bearer; max_completion_tokens, reasoning_effort
    anthropic  POST /v1/messages           x-api-key, anthropic-version 2023-06-01; system, thinking (+ output_config.effort)
    google     POST /v1beta/models/<id>:generateContent   x-goog-api-key; systemInstruction, generationConfig

Reasoning on Anthropic. Two request styles, by model generation (thinking_style):
  adaptive (Claude 4.6 and later, including Haiku 5.5 - verified: it answers 400 to {"type": "enabled"}):
      thinking {"type": "adaptive", "display": "summarized"} + output_config {"effort": "medium"}. The effort is the profile's
      effort as it stands; "display": "summarized" only makes the API return the thinking text (the default omits it) so it
      can be stored as the step's reasoning; it does not change how much the model thinks. max_tokens bounds thinking + answer.
  budget (older models): thinking {"type": "enabled", "budget_tokens": B} with OpenRouter's own mapping from effort,
      B = clamp(max_tokens x ratio, 1024, 128000), ratio minimal .1, low .2, medium .5, high .8, xhigh .95 (OpenRouter's reasoning
      documentation); medium with the runs' 16,384-token cap is 8192.
A price-table entry may force the style with "anthropic_thinking": "adaptive" | "budget".

Errors (strict: the keys are paid). 400, 401, 402, 403 and every other 4xx except 408 and 429 are deterministic: no retry, the
step ends at once with origin `provider_refused` (a stop that is not re-run; the http status and the vendor's error type
are in `api_or_protocol_error`). A 429 whose type says the quota or balance is gone (insufficient_quota, billing) is the same,
except Google's: its 429 RESOURCE_EXHAUSTED is a rate or quota window (the spend-based rate limit, "exceeded your current
quota" per minute), retried like any 429.
429, 408, 5xx (Anthropic 529 included) and timeouts or resets are resent after an exponential wait, at most 3 times
(RETRY_WAITS; Retry-After is honoured up to 60 s), then end as `provider_http_error` / `transport_error`, which are
re-run. A reply the vendor itself refused (content filter, refusal stop) is `provider_refused` too, with its usage billed.
No HTTP status error returns a completion, so the attempt is settled at zero in the ledger; a timed-out attempt is settled at
zero as well (the vendor may still have generated it: the one unaccounted case, bounded by 3 resends x one call).

Cost. tokens x configs/direct-prices.json (one table). Every call goes through a budget ledger of its own scope `direct`
(budget/__init__.py): reserve the highest possible price of the call before the POST, settle the real cost after it. The
ledger file is SCAMWORLD_DIRECT_LEDGER (a run driver can set one per episode), else a new file under results/runs/_ledgers/direct/.
"""
import copy
import datetime
import hashlib
import http.client
import io
import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from decimal import Decimal
from pathlib import Path

from dotenv import dotenv_values

from scamworld.budget import BudgetCallError
from scamworld.paths import CONFIGS, RUNS

VENDORS = ('openai', 'anthropic', 'google')
KEY_NAMES = {'openai': 'OPENAI_API_KEY', 'anthropic': 'ANTHROPIC_API_KEY', 'google': 'GEMINI_API_KEY'}
ENV = 'SCAMWORLD_DIRECT_ENV'
LEDGER_ENV = 'SCAMWORLD_DIRECT_LEDGER'
LIMIT_ENV = 'SCAMWORLD_DIRECT_LIMIT'
DEFAULT_LIMIT = '10'   # USD per ledger (one episode); the agent's own per-episode cap (episode.MAX_COST_USD, 5) stops first
PRICES = CONFIGS / 'direct-prices.json'
URLS = {'openai': 'https://api.openai.com/v1/chat/completions',
        'anthropic': 'https://api.anthropic.com/v1/messages',
        'google': 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'}
ANTHROPIC_VERSION = '2023-06-01'
TIMEOUT = 300           # seconds per request (a 16k-token reasoning answer takes a minute or more)
RETRY_WAITS = (4, 8, 16)   # seconds before resend 1, 2, 3: exponential, at most 3 resends
MAX_RETRY_AFTER = 60
RETRYABLE = (408, 429)   # plus every 5xx
QUOTA_WORDS = ('insufficient_quota', 'billing', 'credit balance', 'exceeded your current quota')
ADAPTIVE_FROM = (4, 6)   # first Claude generation that takes thinking.type "adaptive" (and rejects "enabled" from 5.x on)
CLAUDE_VERSION = re.compile(r'^claude-(?:(?:opus|sonnet|haiku)-(\d+)(?:-(\d{1,2})(?![0-9]))?|(\d+)(?:-(\d{1,2}))?-(?:opus|sonnet|haiku))')
EFFORT_RATIO = {'minimal': 0.1, 'low': 0.2, 'medium': 0.5, 'high': 0.8, 'xhigh': 0.95}   # OpenRouter's reasoning effort ratios
MODEL_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')
DATA_URL = re.compile(r'^data:(image/[A-Za-z0-9.+-]+);base64,(.+)$', re.S)
sleep = time.sleep   # tests replace it


def is_direct(model):
    """True for `openai:<id>`, `anthropic:<id>` and `google:<id>`."""
    return isinstance(model, str) and model.partition(':')[0] in VENDORS and bool(model.partition(':')[2])


def split_model(model):
    if not is_direct(model):
        raise ValueError(f'Not a direct model string: {model!r} (expected openai:<id>, anthropic:<id> or google:<id>)')
    vendor, _, name = model.partition(':')
    if not MODEL_ID.match(name):
        raise ValueError(f'Unsupported characters in the model id of {model!r}')
    return vendor, name


class DirectHTTPError(urllib.error.HTTPError):
    """A non-2xx answer of a vendor API. `origin` is the error origin the step records (episode.error_stop): provider_refused for a
    deterministic refusal, which is not re-run; provider_http_error once the retries of a transient status ran out."""
    def __init__(self, url, code, message, body, vendor, error_type, origin):
        super().__init__(url, code, message, {}, io.BytesIO(body))
        self.vendor, self.vendor_error_type, self.origin = vendor, error_type, origin


class DirectRefused(BudgetCallError):
    """The vendor answered but declined (content filter, safety block, refusal stop). The call's usage is billed and settled; it is a
    BudgetCallError so the agent adds its cost and tokens (response, request and receipt are attached)."""
    origin = 'provider_refused'


def read_key(vendor, env_path=None):
    """The vendor key from the dotenv file SCAMWORLD_DIRECT_ENV. Never printed or logged; errors name the variable, not a value."""
    path = env_path or os.environ.get(ENV)
    if not path:
        raise ValueError(f'No direct key file: set {ENV} to a dotenv file with {KEY_NAMES[vendor]}')
    if not Path(path).is_file():
        raise ValueError(f'{ENV} does not name a file')
    key = (dotenv_values(path, interpolate=False).get(KEY_NAMES[vendor]) or '').strip()
    if not key:
        raise ValueError(f'The {ENV} file has no {KEY_NAMES[vendor]}')
    return key


# ---------------------------------------------------------------- prices and cost

def price_table():
    raw = PRICES.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def price_of(model, table=None, today=None):
    """(entry, basis): the price entry of a model with the dated changes in force today applied, and 'listed' or 'vendor_default'."""
    table = table or price_table()[0]
    vendor, _ = split_model(model)
    entry, basis = table['models'].get(model), 'listed'
    if entry is None:
        entry, basis = table['defaults'][vendor], 'vendor_default'
    entry = copy.deepcopy(entry)
    today = today or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    for change in sorted(entry.pop('changes', []), key=lambda c: c['from']):
        if change['from'] <= today:
            entry.update({k: v for k, v in change.items() if k != 'from'})
            for tier in entry.get('tiers', []):
                tier.update({k: v for k, v in change.items() if k not in ('from', 'above_prompt_tokens')})
    return entry, basis


def _rates(entry, prompt_tokens):
    rate = {k: entry[k] for k in ('input', 'output', 'cached_input') if k in entry}
    for tier in sorted(entry.get('tiers', []), key=lambda t: t['above_prompt_tokens']):
        if prompt_tokens > tier['above_prompt_tokens']:
            rate.update({k: tier[k] for k in ('input', 'output', 'cached_input') if k in tier})
    return rate


def cost_usd(entry, usage):
    """Decimal USD of one call from the normalised usage: uncached prompt x input + cached prompt x cached_input (when the entry has one)
    + completion (reasoning included) x output."""
    prompt, completion = int(usage.get('prompt_tokens') or 0), int(usage.get('completion_tokens') or 0)
    rate = _rates(entry, prompt)
    cached = int((usage.get('prompt_tokens_details') or {}).get('cached_tokens') or 0) if 'cached_input' in rate else 0
    cached = min(max(cached, 0), prompt)
    d = lambda v: Decimal(str(v))
    return ((prompt - cached) * d(rate['input']) + cached * d(rate.get('cached_input', 0)) + completion * d(rate['output'])) / Decimal(1000000)


def ceiling_usd(entry, max_tokens):
    """The most one call can cost: the full context window at the highest input price plus max_tokens at the highest output price."""
    inputs = [entry['input']] + [t['input'] for t in entry.get('tiers', [])]
    outputs = [entry['output']] + [t['output'] for t in entry.get('tiers', [])]
    return (Decimal(entry['context_tokens']) * Decimal(str(max(inputs))) + Decimal(max_tokens) * Decimal(str(max(outputs)))) / Decimal(1000000)


# ---------------------------------------------------------------- request builders (OpenRouter-shaped body -> vendor body)

def _parts(content):
    """Message content as a list of ('text', str) / ('image', mime, base64 | None, url | None)."""
    if isinstance(content, str):
        return [('text', content)]
    out = []
    for part in content or []:
        if part.get('type') == 'text':
            out.append(('text', part['text']))
        elif part.get('type') == 'image_url':
            url = part['image_url']['url']
            m = DATA_URL.match(url)
            out.append(('image', m.group(1), m.group(2), None) if m else ('image', None, None, url))
        else:
            raise ValueError(f'Unsupported content part {part.get("type")!r}')
    return out


def _system_and_turns(messages):
    system = '\n\n'.join(''.join(p[1] for p in _parts(m['content']) if p[0] == 'text') for m in messages if m['role'] == 'system')
    return system, [m for m in messages if m['role'] != 'system']


def _effort(reasoning):
    """The profile's OpenRouter `reasoning` field -> an effort name, or None for reasoning switched off."""
    reasoning = reasoning or {}
    if reasoning.get('enabled') is False or reasoning.get('effort') == 'none':
        return None
    return reasoning.get('effort') or 'medium'


def thinking_budget(max_tokens, effort):
    """OpenRouter's Anthropic mapping: clamp(max_tokens x ratio, 1024, 128000); Anthropic needs it below max_tokens."""
    budget = max(min(int(max_tokens * EFFORT_RATIO[effort]), 128000), 1024)
    if budget >= max_tokens:
        budget = max_tokens - 1
    if budget < 1024:
        raise ValueError(f'max_tokens {max_tokens} is too small for Anthropic extended thinking (budget at least 1024)')
    return budget


def thinking_style(name, forced=None):
    """'adaptive' or 'budget' for an Anthropic model id (claude-haiku-5-5 -> adaptive, claude-sonnet-4-5-20250929 -> budget,
    claude-3-7-sonnet-latest -> budget); an id that does not parse is taken as new, i.e. adaptive."""
    if forced in ('adaptive', 'budget'):
        return forced
    m = CLAUDE_VERSION.match(name)
    if not m:
        return 'adaptive'
    major, minor = (int(m.group(1) or m.group(3)), int(m.group(2) or m.group(4) or 0))
    return 'adaptive' if (major, minor) >= ADAPTIVE_FROM else 'budget'


def openai_request(name, body):
    out = {'model': name, 'messages': copy.deepcopy(body['messages']), 'max_completion_tokens': body['max_tokens']}
    effort = _effort(body.get('reasoning'))
    if effort:
        out['reasoning_effort'] = 'high' if effort == 'xhigh' else effort
    return out


def anthropic_request(name, body, style=None):
    system, turns = _system_and_turns(body['messages'])
    messages = []
    for m in turns:
        blocks = []
        for p in _parts(m['content']):
            if p[0] == 'text':
                if p[1].strip():
                    blocks.append({'type': 'text', 'text': p[1]})
            elif p[2] is not None:
                blocks.append({'type': 'image', 'source': {'type': 'base64', 'media_type': p[1], 'data': p[2]}})
            else:
                blocks.append({'type': 'image', 'source': {'type': 'url', 'url': p[3]}})
        if blocks:
            messages.append({'role': m['role'], 'content': blocks})
    out = {'model': name, 'max_tokens': body['max_tokens'], 'messages': messages}
    if system:
        out['system'] = system
    effort = _effort(body.get('reasoning'))
    if effort and thinking_style(name, style) == 'adaptive':
        out['thinking'] = {'type': 'adaptive', 'display': 'summarized'}
        out['output_config'] = {'effort': 'low' if effort == 'minimal' else 'high' if effort == 'xhigh' else effort}
    elif effort:
        out['thinking'] = {'type': 'enabled', 'budget_tokens': thinking_budget(body['max_tokens'], effort)}
    return out


def google_request(name, body):
    system, turns = _system_and_turns(body['messages'])
    contents = []
    for m in turns:
        parts = []
        for p in _parts(m['content']):
            if p[0] == 'text':
                if p[1].strip():
                    parts.append({'text': p[1]})
            elif p[2] is not None:
                parts.append({'inline_data': {'mime_type': p[1], 'data': p[2]}})
            else:
                raise ValueError('Gemini direct accepts only data-URL images')
        if parts:
            contents.append({'role': 'model' if m['role'] == 'assistant' else 'user', 'parts': parts})
    config = {'maxOutputTokens': body['max_tokens']}
    if body.get('temperature') is not None:
        config['temperature'] = body['temperature']   # as OpenRouter forwarded it (module docstring)
    effort = _effort(body.get('reasoning'))
    if effort:
        config['thinkingConfig'] = {'thinkingLevel': 'high' if effort == 'xhigh' else effort, 'includeThoughts': True}
    out = {'contents': contents, 'generationConfig': config}
    if system:
        out['systemInstruction'] = {'parts': [{'text': system}]}
    return out


BUILDERS = {'openai': openai_request, 'anthropic': anthropic_request, 'google': google_request}


def headers(vendor, key):
    base = {'Content-Type': 'application/json'}
    if vendor == 'openai':
        return base | {'Authorization': 'Bearer ' + key}
    if vendor == 'anthropic':
        return base | {'x-api-key': key, 'anthropic-version': ANTHROPIC_VERSION}
    return base | {'x-goog-api-key': key}


# ---------------------------------------------------------------- responses (vendor -> OpenRouter shape)

def _n(value):
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def _shape(vendor, rid, content, reasoning, finish, usage):
    message = {'role': 'assistant', 'content': content}
    if reasoning:
        message['reasoning'] = reasoning
    return {'id': rid, 'provider': vendor, 'choices': [{'index': 0, 'message': message, 'finish_reason': finish}], 'usage': usage}


def openai_response(raw):
    choice = (raw.get('choices') or [{}])[0]
    message = choice.get('message') or {}
    usage = raw.get('usage') if isinstance(raw.get('usage'), dict) else None
    out = copy.deepcopy(raw)
    out['provider'] = 'openai'
    if usage is not None:
        out['usage'] = {'prompt_tokens': _n(usage.get('prompt_tokens')), 'completion_tokens': _n(usage.get('completion_tokens')),
                        'completion_tokens_details': {'reasoning_tokens': _n((usage.get('completion_tokens_details') or {}).get('reasoning_tokens'))},
                        'prompt_tokens_details': {'cached_tokens': _n((usage.get('prompt_tokens_details') or {}).get('cached_tokens'))}}
    refused = bool(message.get('refusal')) or choice.get('finish_reason') == 'content_filter'
    return out, usage is not None, (str(message.get('refusal') or 'content_filter')[:300] if refused and not message.get('content') else None)


def anthropic_response(raw):
    blocks = raw.get('content') if isinstance(raw.get('content'), list) else []
    text = ''.join(b.get('text') or '' for b in blocks if isinstance(b, dict) and b.get('type') == 'text')
    thinking = '\n'.join(b.get('thinking') or '' for b in blocks if isinstance(b, dict) and b.get('type') == 'thinking').strip()
    stop = raw.get('stop_reason')
    finish = {'end_turn': 'stop', 'stop_sequence': 'stop', 'max_tokens': 'length', 'refusal': 'content_filter', 'tool_use': 'tool_calls'}.get(stop, stop)
    u = raw.get('usage') if isinstance(raw.get('usage'), dict) else None
    usage = None
    if u is not None:   # output_tokens already includes the thinking tokens; Anthropic does not report them apart
        usage = {'prompt_tokens': _n(u.get('input_tokens')) + _n(u.get('cache_read_input_tokens')) + _n(u.get('cache_creation_input_tokens')),
                 'completion_tokens': _n(u.get('output_tokens'))}
    out = _shape('anthropic', raw.get('id'), text, thinking, finish, usage)
    if any(isinstance(b, dict) and b.get('type') == 'redacted_thinking' for b in blocks):
        out['choices'][0]['message']['reasoning_details'] = [{'type': 'reasoning.encrypted'}]
    return out, usage is not None, ('stop_reason refusal' if stop == 'refusal' and not text else None)


def google_response(raw):
    candidates = raw.get('candidates') if isinstance(raw.get('candidates'), list) else []
    cand = candidates[0] if candidates and isinstance(candidates[0], dict) else {}
    parts = (cand.get('content') or {}).get('parts') or []
    text = ''.join(p.get('text') or '' for p in parts if isinstance(p, dict) and not p.get('thought'))
    thought = '\n'.join(p.get('text') or '' for p in parts if isinstance(p, dict) and p.get('thought')).strip()
    reason = cand.get('finishReason')
    finish = {'STOP': 'stop', 'MAX_TOKENS': 'length'}.get(reason, 'content_filter' if reason in (
        'SAFETY', 'RECITATION', 'BLOCKLIST', 'PROHIBITED_CONTENT', 'SPII', 'IMAGE_SAFETY', 'IMAGE_PROHIBITED_CONTENT') else (reason or '').lower() or None)
    u = raw.get('usageMetadata') if isinstance(raw.get('usageMetadata'), dict) else None
    usage = None
    if u is not None:   # thoughtsTokenCount is billed as output and not part of candidatesTokenCount
        modal = {d.get('modality'): _n(d.get('tokenCount')) for d in u.get('promptTokensDetails') or [] if isinstance(d, dict)}
        thoughts = _n(u.get('thoughtsTokenCount'))
        usage = {'prompt_tokens': _n(u.get('promptTokenCount')), 'completion_tokens': _n(u.get('candidatesTokenCount')) + thoughts,
                 'completion_tokens_details': {'reasoning_tokens': thoughts},
                 'prompt_tokens_details': {'image_tokens': modal.get('IMAGE', 0), 'cached_tokens': _n(u.get('cachedContentTokenCount'))}}
    out = _shape('google', raw.get('responseId'), text, thought, finish, usage)
    blocked = (raw.get('promptFeedback') or {}).get('blockReason')
    refusal = ('prompt blocked: ' + str(blocked)) if blocked and not candidates else ('finishReason ' + str(reason) if finish == 'content_filter' and not text else None)
    return out, usage is not None, refusal


NORMALIZERS = {'openai': openai_response, 'anthropic': anthropic_response, 'google': google_response}


def error_info(vendor, raw_body):
    """(vendor error type, message) from an error body; both short strings, '' when absent."""
    try:
        error = json.loads(raw_body).get('error')
    except (ValueError, AttributeError):
        return '', ''
    if isinstance(error, dict):
        kind = error.get('type') if vendor in ('openai', 'anthropic') else error.get('status')
        return str(kind or error.get('code') or ''), str(error.get('message') or '')[:300]
    return '', str(error or '')[:300]


# ---------------------------------------------------------------- HTTP

def http_post(url, header_map, data, timeout):
    """One POST. Returns (status, response headers, body bytes) for any HTTP status; network failures raise URLError / TimeoutError
    (resets and short reads are wrapped as URLError, as gateway_post does). The tests replace this function."""
    request = urllib.request.Request(url, data=data, headers=header_map)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers or {}), error.read()
    except (urllib.error.URLError, TimeoutError):
        raise
    except (OSError, http.client.HTTPException) as error:
        raise urllib.error.URLError(error) from error


def _retry_after(headers_in):
    for k, v in (headers_in or {}).items():
        if k.lower() == 'retry-after':
            try:
                return min(max(float(v), 0), MAX_RETRY_AFTER)
            except (TypeError, ValueError):
                return 0
    return 0


class DirectTransport:
    """One model's direct client, with the budget ledger. complete() has the signature of budget.BudgetedTransport.complete and returns
    (normalised response, vendor request body, receipt)."""

    def __init__(self, model, ledger_path=None, limit=None):
        from scamworld.budget import BudgetLedger
        self.model = model
        self.vendor, self.name = split_model(model)
        table, digest = price_table()
        self.entry, self.basis = price_of(model, table)
        path = ledger_path or os.environ.get(LEDGER_ENV)
        if not path:
            path = RUNS / '_ledgers' / 'direct' / f'{time.strftime("%Y%m%d-%H%M%S")}-{os.getpid()}-{uuid.uuid4().hex[:8]}.sqlite'
        self.ledger = BudgetLedger(path, scope='direct', limit=limit or os.environ.get(LIMIT_ENV) or DEFAULT_LIMIT, policy_sha256=digest)

    def prepare(self, body):
        """Vendor request body, URL and the reservation ceiling of an OpenRouter-shaped body."""
        tokens = body.get('max_tokens')
        if type(tokens) is not int or not 1 <= tokens <= 200000:
            raise ValueError('A bounded integer max_tokens (reasoning counted against it) is required')
        vendor_body = BUILDERS[self.vendor](self.name, body, *([self.entry.get('anthropic_thinking')] if self.vendor == 'anthropic' else []))
        return vendor_body, URLS[self.vendor].format(model=self.name), ceiling_usd(self.entry, tokens)

    def complete(self, body, key, *, caller='agent', retries=None, times=None):
        vendor_body, url, ceiling = self.prepare(body)
        encoded = json.dumps(vendor_body, ensure_ascii=False, allow_nan=False).encode()
        digest = hashlib.sha256(encoded).hexdigest()
        header_map = headers(self.vendor, key)
        redact = lambda s: str(s).replace(key, '[REDACTED]')
        for attempt in range(len(RETRY_WAITS) + 1):
            request_id = self.ledger.reserve(model=self.model, caller=caller, request_sha256=digest, upper_usd=ceiling)
            receipt = {'request_id': request_id, 'scope': 'direct', 'transport': 'direct', 'policy_sha256': self.ledger.policy_sha256,
                       'reserved_microusd': int((ceiling * 1000000).to_integral_value(rounding='ROUND_CEILING')), 'price_basis': self.basis}
            started = time.monotonic()
            try:
                status, response_headers, raw = http_post(url, header_map, encoded, TIMEOUT)
            except (urllib.error.URLError, TimeoutError) as error:   # nothing came back; resent (see the module docstring on billing)
                if times is not None:
                    times.append(round(time.monotonic() - started, 3))
                self.ledger.settle(request_id, 0)
                if attempt >= len(RETRY_WAITS):
                    raise
                if retries is not None:
                    retries.append({'error_type': type(error).__name__, 'message': redact(error)[:300]})
                sleep(RETRY_WAITS[attempt])
                continue
            except BaseException:
                self.ledger.unknown(request_id, 'request interrupted')
                raise
            if times is not None:
                times.append(round(time.monotonic() - started, 3))
            if not 200 <= status < 300:
                self.ledger.settle(request_id, 0)   # an error status returns no completion and bills nothing
                kind, message = error_info(self.vendor, raw)
                lowered = (kind + ' ' + message).lower()
                transient = status in RETRYABLE or status >= 500
                if status == 429 and self.vendor != 'google' and any(w in lowered for w in QUOTA_WORDS):
                    transient = False   # out of quota or balance: a resend only repeats it (Google's 429 is a rate window)
                if transient and attempt < len(RETRY_WAITS):
                    if retries is not None:
                        retries.append({'error_type': 'HTTPError', 'http_status': status, 'vendor_error_type': kind, 'message': redact(message)[:300]})
                    sleep(max(RETRY_WAITS[attempt], _retry_after(response_headers)))
                    continue
                origin = 'provider_http_error' if transient else 'provider_refused'
                raise DirectHTTPError(url, status, redact(f'{kind}: {message}' if kind else message or 'error'), redact(raw.decode(errors='replace')).encode(),
                                      self.vendor, kind, origin)
            try:
                parsed = json.loads(raw)
                if not isinstance(parsed, dict):
                    raise ValueError('not an object')
                result, has_usage, refusal = NORMALIZERS[self.vendor](parsed)
            except (ValueError, TypeError, AttributeError) as error:   # a completed call whose body cannot be read: billing unknown
                from scamworld.budget import UnknownBilling
                self.ledger.unknown(request_id, 'unreadable 2xx body')
                raise UnknownBilling('Provider answered 2xx with a body that cannot be read; billing unknown', request_body=vendor_body, receipt=receipt) from error
            if not has_usage:
                from scamworld.budget import UnknownBilling
                self.ledger.unknown(request_id, 'no usage in the response')
                raise UnknownBilling('Provider response carries no usage; billing unknown', response=result, request_body=vendor_body, receipt=receipt)
            cost = cost_usd(self.entry, result['usage'])
            result['usage']['cost'] = float(cost)
            result['transport'] = 'direct'
            try:
                self.ledger.settle(request_id, cost, generation_id=result.get('id'))
            except Exception as error:   # returned cost above the reservation: recorded, the ledger is halted
                from scamworld.budget import BudgetCallError, BudgetError
                if isinstance(error, BudgetError):
                    receipt['actual_cost_usd'] = str(cost)
                    raise BudgetCallError(str(error), response=result, request_body=vendor_body, receipt=receipt) from error
                raise
            receipt |= {'actual_cost_usd': str(cost), 'generation_id': result.get('id')}
            if refusal:
                raise DirectRefused(redact(f'{self.vendor} declined the request: {refusal}'), response=result, request_body=vendor_body, receipt=receipt)
            return result, vendor_body, receipt
        raise AssertionError('unreachable')
