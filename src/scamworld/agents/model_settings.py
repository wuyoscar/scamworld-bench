"""Agent backbone request settings per reasoning profile (configs/agent-models.json).

The profile is SCAMWORLD_REASONING_PROFILE (the experiment option reasoning_profile sets it), else the file's default_profile
('r8'). Profile 'r7' reproduces the r7 requests exactly; 'r8' runs every backbone that supports reasoning at medium effort with
a larger output cap. Agent backbones only: the judge keeps its frozen settings (scoring/judge.py).

    settings(model) -> {'profile', 'max_tokens', 'reasoning' (OpenRouter field),
                        'extra' (request-body keys for the free model gateway, cz/ models; or None)}
"""
import copy
import json
import os

from scamworld.paths import CONFIGS

CONFIG = CONFIGS / 'agent-models.json'
ENV = 'SCAMWORLD_REASONING_PROFILE'
INTERFACE = 'r8'   # agent-visible interface of this repository (sites as served, action-error messages); recorded in score.json


def _config():
    return json.loads(CONFIG.read_text(encoding='utf-8'))


def profile_name(config=None):
    config = config or _config()
    name = os.environ.get(ENV) or config['default_profile']
    if name not in config['profiles']:
        raise ValueError(f'Unknown reasoning profile {name!r} ({ENV}); defined: {", ".join(sorted(config["profiles"]))}')
    return name


def settings(model, profile=None):
    """Request settings of one agent backbone under the given (or the active) profile."""
    config = _config()
    name = profile or profile_name(config)
    if name not in config['profiles']:
        raise ValueError(f'Unknown reasoning profile {name!r}; defined: {", ".join(sorted(config["profiles"]))}')
    prof = config['profiles'][name]
    entry = prof.get('models', {}).get(model, {})
    out = {'profile': name, **copy.deepcopy(prof['default']), **copy.deepcopy(entry)}
    out.setdefault('extra', None)
    if model.startswith('cz/') and out['extra'] is None:
        raise ValueError(f'No gateway request settings for {model!r} in profile {name!r} ({CONFIG.name})')
    return out
