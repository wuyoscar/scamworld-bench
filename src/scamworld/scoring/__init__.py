"""Versioned entry points for episode evaluation."""
from .v1 import evaluate as evaluate_v1


def evaluator(name='v1'):
    if name == 'v1':
        return evaluate_v1
    if name == 'v2':
        from .v2 import evaluate as evaluate_v2
        return evaluate_v2
    raise ValueError('Unknown evaluator: ' + str(name))
