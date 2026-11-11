"""Named observation/action configurations; they never change the task or scorer."""
from dataclasses import dataclass

@dataclass(frozen=True)
class InteractionProfile:
    observations: tuple[str, ...]
    actions: tuple[str, ...]
    description: str

PROFILES = {
    'screenshot': InteractionProfile(('screenshot',), ('bid', 'coord'),
        'Raw viewport image and URL; coordinate clicks, shared form typing and answer contract.'),
    'som': InteractionProfile(('som',), ('bid', 'coord'),
        'Viewport image with BrowserGym control marks and URL.'),
    'ax': InteractionProfile(('ax_tree',), ('bid',),
        'Accessibility tree with BrowserGym IDs and URL; no image.'),
    'html': InteractionProfile(('html',), ('bid',),
        'Pruned DOM with BrowserGym IDs and URL; no image.'),
    'combined': InteractionProfile(('screenshot', 'ax_controls'), ('bid',),
        'Historical default: raw screenshot plus accessibility control list.'),
    'combined-navigation': InteractionProfile(('screenshot', 'ax_tree', 'html'),
        ('bid', 'coord', 'hover', 'nav', 'tabs'),
        'Combined views with coordinates, hover, navigation and tabs.'),
}
DEFAULT_PROFILE = 'combined'


def resolve_profile(name=DEFAULT_PROFILE):
    if name not in PROFILES:
        raise ValueError(f'Unknown interaction_profile {name!r}; choose {", ".join(PROFILES)}')
    return PROFILES[name]


def profile_kwargs(name=DEFAULT_PROFILE):
    p = resolve_profile(name)
    return {'obs_modes': ','.join(p.observations), 'action_modes': ','.join(p.actions)}


ID_SOURCES = {'som', 'ax_controls', 'ax_tree', 'html'}   # observations that show the agent element IDs (bid)


def default_actions(observations):
    """The action modes used when none are given: element IDs when the observation shows them, else screen coordinates."""
    om = {m.strip() for m in (observations or '').split(',') if m.strip()}
    return 'bid' if om & ID_SOURCES else 'coord'


def parse_modes(observations, actions):
    om = {m.strip() for m in observations.split(',') if m.strip()}
    am = {m.strip() for m in actions.split(',') if m.strip()}
    bad = om - {'screenshot', 'som', 'ax_controls', 'ax_tree', 'html'}
    bad |= am - {'bid', 'coord', 'hover', 'nav', 'tabs'}
    if bad or not om or not am & {'bid', 'coord'}:   # coord alone is the screenshot condition (BrowserGym's coord set)
        raise ValueError(f'Bad modality config: obs={observations} actions={actions}')
    # An observation without element IDs cannot drive ID actions; every click would be refused and the episode
    # would end after three refusals. Say so up front instead.
    if 'bid' in am and 'coord' not in am and not om & ID_SOURCES:
        raise ValueError(f'obs={observations} shows the agent no element IDs, so actions={actions} cannot work: '
                         f'use actions coord (or bid,coord), or add som, ax_controls, ax_tree or html to the observation')
    return om, am
