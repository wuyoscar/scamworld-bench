"""Process settings applied before AgentLab/BrowserGym are imported.

Library state lives in .cache/, and AgentLab / BrowserGym experiments are installed from vendor/ by uv instead of being
put on sys.path.
"""
import os
import sys

from scamworld.paths import CACHE

os.environ['AGENTLAB_EXP_ROOT'] = str(CACHE / 'agentlab')
os.environ.setdefault('NLTK_DATA', str(CACHE / 'nltk'))   # an already set NLTK_DATA (e.g. a shared nltk_data) is kept
os.environ.setdefault('IPYTHONDIR', str(CACHE / 'ipython'))
sys.dont_write_bytecode = True
