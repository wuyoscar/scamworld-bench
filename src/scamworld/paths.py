"""Repository locations. Every path is relative to the repository root (the folder that holds pyproject.toml).

Environment overrides: SCAMWORLD_HOME (another checkout or an unpacked release), SCAMWORLD_TASKS (another task folder, e.g.
your own tasks made with `scamworld new-task`), SCAMWORLD_ENV_FILE and SCAMWORLD_OPENWEIGHTS_ENV_FILE (key files; default .env and
.env.openweights in the repository root). The judge key file falls back to the agent key file when it does not exist, so a single
.env with OPENROUTER_API_KEY serves both.
"""
import os
from pathlib import Path

REPO = Path(os.environ.get('SCAMWORLD_HOME') or Path(__file__).resolve().parents[2])
TASKS = Path(os.environ.get('SCAMWORLD_TASKS') or REPO / 'tasks')   # one folder per task (docs/task-format.md)
RELEASE = REPO / 'release'             # path-map.json: the release manifest `scamworld check` verifies
# model settings (agent-models.json), direct-API prices and the endpoints example; the budget policies, the model
# gateway address (gateway.json) and the coordinate calibration are only in the source repository
CONFIGS = REPO / 'configs'
# EXPERIMENTS and ANALYSIS are folders of the source repository that are not part of this release (template instances,
# the fake-element copies, the asked-directly task texts and the task lists of some plans); a plan that reads them
# refuses when an input is missing.
EXPERIMENTS = REPO / 'experiments'
ANALYSIS = REPO / 'analysis'
RESULTS = REPO / 'results'             # run outputs (not in git)
RUNS = RESULTS / 'runs'                # results/runs/<experiment>/<model>/<config>/<task>/r<k>/
WORK = RESULTS / 'sitekit'             # per-task pilot runs and browser checks (scamworld run / verify)
CACHE = REPO / '.cache'                # library state: AgentLab study root, NLTK data, IPython dir (not in git)
ENV_FILE = Path(os.environ.get('SCAMWORLD_ENV_FILE') or REPO / '.env')


def judge_env_file(judge_file, agent_file):
    """The judge key file: judge_file, or agent_file when judge_file does not exist and agent_file does."""
    judge_file, agent_file = Path(judge_file), Path(agent_file)
    return agent_file if not judge_file.is_file() and agent_file.is_file() else judge_file


OPENWEIGHTS_ENV_FILE = judge_env_file(os.environ.get('SCAMWORLD_OPENWEIGHTS_ENV_FILE') or REPO / '.env.openweights', ENV_FILE)
