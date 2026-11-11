"""Opt-in durable model-call budget ledger; unknown billing never becomes zero.

The ledger is an accounting layer for runs that must record every call. It is off when neither SCAMWORLD_BUDGET_LEDGER nor
SCAMWORLD_BUDGET_POLICY (a pricing policy file) is set (setting only one is an error); without them the default agent model
and the OpenRouter judge model are called directly through OpenRouter and billed to the caller's key, like any other
OpenRouter model. SCAMWORLD_BUDGET_REQUIRED=1 makes those two models refuse to run without the ledger (see require_budget).

With the ledger on, a request is reserved and committed before POST. Provider price ceilings and a pinned context bound
define its reservation. Pending/unknown requests block any new dispatch, including after process restart. A request whose
outcome is unknown is never retried; an HTTP error status (no completion, not billed) is settled at zero and retried with
backoff only for HTTP_RETRY_STATUS.
"""
import copy
import hashlib
import json
import os
import sqlite3
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from pathlib import Path

# Per scope: the highest limit (USD) a ledger accepts and, for 'experiment' and 'annotation', the models whose calls it
# admits; scope 'direct' admits model strings of the three vendors (_DirectModels).
LIMITS = {'experiment': Decimal('10'), 'annotation': Decimal('15'), 'direct': Decimal('25')}
MODELS = {'experiment': frozenset({'google/gemma-4-31b-it'}),
          'annotation': frozenset({'openai/gpt-5.6-terra', 'x-ai/grok-4.7'})}
# deepseek/deepseek-v4.1-flash is not an agent model of the ledger: the provider its pricing policy pins runs the model in
# 4-bit precision (fp4) and reduces a screenshot to about 57 tokens, so agents use deepseek/deepseek-v4.1-flash-1017 on
# Together instead (configs/agent-models.json). In the ledger only the text-only judge may call it (experiment scope).
JUDGE_MODELS = frozenset({'deepseek/deepseek-v4.1-flash'})
SCALE = Decimal('1000000')
HTTP_RETRY_STATUS = (408, 429, 500, 502, 503, 504)
HTTP_RETRY_WAITS = (5, 15, 30, 60, 90)   # seconds; then the HTTPError reaches the caller (cost known, zero)


class BudgetError(ValueError):
    """No further request may be sent under the current budget state."""


class BudgetCallError(BudgetError):
    cost_known = True
    def __init__(self, message, response=None, request_body=None, receipt=None):
        super().__init__(message)
        self.response, self.request_body, self.receipt = response, request_body, receipt


class UnknownBilling(BudgetCallError):
    cost_known = False


def amount(value):
    if isinstance(value, bool) or value is None:
        raise BudgetError('An explicit finite nonnegative USD amount is required')
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise BudgetError('Invalid USD amount') from error
    if not result.is_finite() or result < 0:
        raise BudgetError('An explicit finite nonnegative USD amount is required')
    return result


class _DirectModels:
    """Scope 'direct' (agents/direct.py): any model string of the three vendors, openai:<id>, anthropic:<id> or google:<id>."""
    def __contains__(self, model):
        return isinstance(model, str) and model.partition(':')[0] in ('openai', 'anthropic', 'google') and bool(model.partition(':')[2])


def authorized(scope, caller):
    if scope == 'direct':
        return _DirectModels()
    return MODELS[scope] | (JUDGE_MODELS if scope == 'experiment' and caller == 'judge' else frozenset())


def micros(value):
    return int((amount(value) * SCALE).to_integral_value(rounding=ROUND_CEILING))


class BudgetLedger:
    def __init__(self, path, *, scope, limit, policy_sha256):
        if scope not in LIMITS:
            raise BudgetError(f'unknown budget scope {scope!r} (one of: {", ".join(LIMITS)})')
        if not 0 < amount(limit) <= LIMITS[scope]:
            raise BudgetError(f'the budget limit must be above 0 and at most {LIMITS[scope]} USD for scope {scope!r}')
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.scope, self.limit, self.policy_sha256 = scope, micros(limit), policy_sha256
        if not isinstance(policy_sha256, str) or len(policy_sha256) != 64:
            raise BudgetError('A bound pricing policy digest is required')
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE IF NOT EXISTS budget (id INTEGER PRIMARY KEY CHECK(id=1), scope TEXT NOT NULL, cap INTEGER NOT NULL, policy TEXT NOT NULL, halted TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS calls (id TEXT PRIMARY KEY, model TEXT NOT NULL, caller TEXT NOT NULL, request_sha256 TEXT NOT NULL, reserved INTEGER NOT NULL, actual INTEGER, actual_raw TEXT, status TEXT NOT NULL, generation_id TEXT, created REAL NOT NULL, finished REAL, error TEXT)')
            row = db.execute('SELECT scope,cap,policy FROM budget WHERE id=1').fetchone()
            if row is None:
                db.execute('INSERT INTO budget(id,scope,cap,policy) VALUES(1,?,?,?)', (scope,self.limit,policy_sha256))
            elif row != (scope,self.limit,policy_sha256):
                raise BudgetError('Existing budget scope, cap or policy differs; do not reset it')
            db.commit()

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        try:
            db.execute('PRAGMA synchronous=FULL')
            with db:
                yield db
        finally:
            db.close()

    def reserve(self, *, model, caller, request_sha256, upper_usd):
        if model not in authorized(self.scope, caller):
            raise BudgetError('Model is outside this authorized budget scope')
        reserve = micros(upper_usd)
        if reserve <= 0 or len(request_sha256) != 64:
            raise BudgetError('Positive request reservation and body digest required')
        request_id = str(uuid.uuid4())
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            halted = db.execute('SELECT halted FROM budget WHERE id=1').fetchone()[0]
            if halted:
                raise BudgetError('Budget halted: ' + halted)
            if db.execute("SELECT 1 FROM calls WHERE status IN ('reserved','unknown') LIMIT 1").fetchone():
                raise BudgetError('Unsettled previous request; no dispatch or replay allowed')
            spent = db.execute('SELECT COALESCE(SUM(actual),0) FROM calls').fetchone()[0]
            if spent + reserve > self.limit:
                raise BudgetError('Insufficient aggregate budget for this bounded request')
            db.execute('INSERT INTO calls(id,model,caller,request_sha256,reserved,status,created) VALUES(?,?,?,?,?,?,?)',
                       (request_id,model,caller,request_sha256,reserve,'reserved',time.time()))
            db.commit()
        return request_id

    def settle(self, request_id, cost, *, generation_id=None):
        try:
            raw, actual = str(amount(cost)), micros(cost)
        except BudgetError:
            self.unknown(request_id, 'Missing or invalid returned cost', generation_id=generation_id)
            raise UnknownBilling('Missing or invalid returned cost; budget halted')
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT reserved,status,actual,actual_raw,generation_id FROM calls WHERE id=?',(request_id,)).fetchone()
            if row is None:
                raise BudgetError('Unknown reservation')
            reserved, status, previous, previous_raw, previous_generation = row
            if status == 'settled' and (actual,raw,generation_id)==(previous,previous_raw,previous_generation):
                return
            if status != 'reserved':
                raise BudgetError('Reservation already settled or has unknown billing')
            db.execute("UPDATE calls SET actual=?,actual_raw=?,status='settled',generation_id=?,finished=? WHERE id=?",(actual,raw,generation_id,time.time(),request_id))
            if actual > reserved:
                db.execute('UPDATE budget SET halted=? WHERE id=1',('Returned cost exceeded request ceiling',))
            db.commit()
        if actual > reserved:
            raise BudgetError('Returned cost exceeded reservation; actual charge recorded and budget halted')

    def unknown(self, request_id, error, *, generation_id=None):
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            changed = db.execute("UPDATE calls SET status='unknown',error=?,generation_id=?,finished=? WHERE id=? AND status='reserved'",(str(error)[:300],generation_id,time.time(),request_id)).rowcount
            if changed:
                db.execute('UPDATE budget SET halted=? WHERE id=1',('Unknown billing; do not resend request',))
            db.commit()

    def snapshot(self):
        with self._connect() as db:
            scope,cap,policy,halted = db.execute('SELECT scope,cap,policy,halted FROM budget WHERE id=1').fetchone()
            db.row_factory = sqlite3.Row
            calls = [dict(row) for row in db.execute('SELECT * FROM calls ORDER BY created,id')]
        spent = sum(r['actual'] or 0 for r in calls)
        held = sum(r['reserved'] for r in calls if r['status'] in ('reserved','unknown'))
        return {'scope':scope,'cap_microusd':cap,'policy_sha256':policy,'halted':halted,
                'known_spent_microusd':spent,'held_microusd':held,'available_microusd':max(0,cap-spent-held),'calls':calls}


class BudgetedTransport:
    def __init__(self, ledger_path, policy_path, *, scope, limit, env_file):
        self.policy_path = Path(policy_path).resolve()
        raw = self.policy_path.read_bytes()
        self.policy = json.loads(raw)
        self.scope = scope
        required = '.env.openweights' if scope == 'experiment' else '.env'
        if Path(env_file).resolve().name != required:
            raise BudgetError('Budget key-file scope mismatch')
        self.ledger = BudgetLedger(ledger_path,scope=scope,limit=limit,policy_sha256=hashlib.sha256(raw).hexdigest())

    def prepare(self, body, caller='agent'):
        body = copy.deepcopy(body)
        model = body.get('model')
        if model not in authorized(self.scope, caller):
            raise BudgetError('Model is outside this authorized budget scope')
        profile = self.policy['models'].get(model)
        if not profile:
            raise BudgetError('Model has no bound pricing/context profile')
        if set(body) - {'model','messages','temperature','max_tokens','reasoning','response_format','usage'}:
            raise BudgetError('Unbudgeted request fields or add-ons are not allowed')
        tokens = body.get('max_tokens')
        if type(tokens) is not int or not 1 <= tokens <= profile['max_output_tokens']:
            raise BudgetError('A bounded max_tokens including reasoning is required')
        context = profile['context_tokens']
        if type(context) is not int or context <= 0:
            raise BudgetError('Invalid model context bound')
        prompt, completion = amount(profile['prompt_usd_per_million']),amount(profile['completion_usd_per_million'])
        if prompt <= 0 or completion <= 0 or not profile.get('provider'):
            raise BudgetError('Explicit positive token prices and pinned provider required')
        messages = body.get('messages')
        if not isinstance(messages,list) or not messages:
            raise BudgetError('Nonempty messages required')
        for message in messages:
            content = message.get('content') if isinstance(message,dict) else None
            if isinstance(content,str):
                continue
            if not isinstance(content,list):
                raise BudgetError('Only text and local screenshot content are budgeted')
            for part in content:
                if not isinstance(part,dict):
                    raise BudgetError('Invalid message content')
                if part.get('type')=='text' and isinstance(part.get('text'),str):
                    continue
                url = (part.get('image_url') or {}).get('url') if isinstance(part.get('image_url'),dict) else None
                if part.get('type')=='image_url' and isinstance(url,str) and url.startswith(('data:image/png;base64,','data:image/jpeg;base64,','data:image/webp;base64,')):
                    continue
                raise BudgetError('Only text and local screenshot content are budgeted')
        body['provider'] = {'only':[profile['provider']],'allow_fallbacks':False,'require_parameters':True,
                            'max_price':{'prompt':float(prompt),'completion':float(completion),'request':0,'image':0}}
        body['usage'] = {'include':True}
        # Input is reserved at the complete pinned model context, including image
        # tokens; output max_tokens includes reasoning. Separate fees (request, image) are capped at 0.
        ceiling = (context*prompt + tokens*completion)/SCALE
        return body, ceiling

    def complete(self, body, key, *, caller):
        prepared, ceiling = self.prepare(body, caller)
        encoded = json.dumps(prepared,ensure_ascii=False,allow_nan=False).encode()
        for attempt in range(len(HTTP_RETRY_WAITS)+1):
            request_id = self.ledger.reserve(model=prepared['model'],caller=caller,request_sha256=hashlib.sha256(encoded).hexdigest(),upper_usd=ceiling)
            receipt = {'request_id':request_id,'policy_sha256':self.ledger.policy_sha256,'reserved_microusd':micros(ceiling),'scope':self.scope}
            req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',data=encoded,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
            try:
                with urllib.request.urlopen(req,timeout=60) as response:
                    result = json.load(response)
                break
            except urllib.error.HTTPError as error:
                # An HTTP error status means OpenRouter returned no completion, which it does not bill
                # (upstream 429s on a pinned provider can end a large share of the episodes). Settle at zero;
                # retry transient statuses with backoff so the episode, not a lucky subsample, gets scored.
                self.ledger.settle(request_id,0)
                if error.code in HTTP_RETRY_STATUS and attempt < len(HTTP_RETRY_WAITS):
                    time.sleep(HTTP_RETRY_WAITS[attempt]); continue
                raise
            except Exception as error:
                # A failed POST/read may already have generated/billed a completion.
                self.ledger.unknown(request_id,type(error).__name__)
                raise UnknownBilling('Request outcome unknown; do not retry',request_body=prepared,receipt=receipt) from error
        if not isinstance(result,dict):
            self.ledger.unknown(request_id,'Nonobject API response')
            raise UnknownBilling('Request billing unknown',response=result,request_body=prepared,receipt=receipt)
        usage = result.get('usage')
        cost = usage.get('cost') if isinstance(usage,dict) else None
        try:
            self.ledger.settle(request_id,cost,generation_id=result.get('id'))
        except UnknownBilling as error:
            raise UnknownBilling(str(error),response=result,request_body=prepared,receipt=receipt) from error
        except BudgetError as error:
            receipt['actual_cost_usd'] = str(amount(cost))
            raise BudgetCallError(str(error),response=result,request_body=prepared,receipt=receipt) from error
        return result, prepared, {'request_id':request_id,'policy_sha256':self.ledger.policy_sha256,
                                  'reserved_microusd':micros(ceiling),'actual_cost_usd':str(amount(cost)),
                                  'generation_id':result.get('id'),'scope':self.scope}


def transport_from_env(env_file):
    ledger = os.environ.get('SCAMWORLD_BUDGET_LEDGER')
    policy = os.environ.get('SCAMWORLD_BUDGET_POLICY')
    if not ledger and not policy:
        return None
    if not ledger or not policy:
        raise BudgetError('Both shared budget ledger and bound policy are required')
    scope = os.environ.get('SCAMWORLD_BUDGET_SCOPE','experiment')
    return BudgetedTransport(ledger,policy,scope=scope,limit=os.environ.get('SCAMWORLD_BUDGET_LIMIT','10'),env_file=env_file)


def require_budget(model, transport, caller='agent'):
    """With SCAMWORLD_BUDGET_REQUIRED=1, ledger-scoped models refuse to run without a ledger transport.

    Otherwise the ledger is opt-in: without it these models are called directly through OpenRouter (plain POST, billed to
    the caller's key). A ledger transport, when configured, is always used for them (transport_from_env)."""
    required = os.environ.get('SCAMWORLD_BUDGET_REQUIRED') == '1'
    if transport is None and required and model in authorized('experiment', caller):
        raise BudgetError('SCAMWORLD_BUDGET_REQUIRED=1: this model requires SCAMWORLD_BUDGET_LEDGER and '
                          'SCAMWORLD_BUDGET_POLICY before dispatch')
