"""Evaluator v1: the rule score of scoring/score.py (score.score), with the optional in-episode LLM judge."""
from . import score as _module


def evaluate(contract, trace, scoring_spec, llm_judge=None):
    return _module.score(contract, trace, scoring_spec, llm_judge)
