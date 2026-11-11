"""A minimal agent with no model: it clicks buttons named like "pay" / "confirm" (each once), then reports back.

On the scam template task it opens the payment dialog and pays: the episode ends as Deceived.

Shows the gym-style loop of scamworld.gym (docs/custom-agents.md); replace act() with your own policy.

    uv run python examples/agents/scripted_agent.py examples/tasks/parcel-fee-01
"""
import sys

from scamworld.gym import Agent, run_episode


class ScriptedAgent(Agent):
    """Clicks up to `clicks` buttons whose names contain one of `words`, then finishes with a fixed message."""

    def __init__(self, words=('pay', 'confirm', 'continue', 'submit'), clicks=2):
        self.words, self.clicks = words, clicks

    def reset(self, goal, system_prompt):
        self.goal, self.done, self.clicked = goal, 0, set()

    def act(self, obs):
        if self.done < self.clicks:
            for c in obs.get('controls', []):
                name = str(c.get('name', '')).lower()
                if c.get('bid') and c['bid'] not in self.clicked and c.get('role') in ('button', 'link') and any(w in name for w in self.words):
                    self.done += 1
                    self.clicked.add(c['bid'])
                    return {'action': 'click', 'bid': c['bid']}
        return {'action': 'finish', 'message': 'I clicked through the payment steps as asked.'}


if __name__ == '__main__':
    result = run_episode(sys.argv[1] if len(sys.argv) > 1 else 'examples/tasks/parcel-fee-01', ScriptedAgent(), evaluator='rules')
    print(result)
