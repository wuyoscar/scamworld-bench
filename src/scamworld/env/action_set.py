"""Owned BrowserGym action set: single-dispatch, bounded BID clicks."""
from typing import Literal
from browsergym.core.action.highlevel import ACTION_SUBSETS, HighLevelActionSet


def click(
    bid: str,
    button: Literal["left", "middle", "right"] = "left",
    modifiers: list[Literal["Alt", "Control", "ControlOrMeta", "Meta", "Shift"]] = [],
):
    """Click an element once, with a three-second total action budget.

    Examples:
        click('42')
        click('42', button="right")
    """
    # BrowserGym includes these helpers and page in the generated action context.
    elem = get_elem_by_bid(page, bid, demo_mode != "off")
    add_demo_mode_effects(page, elem, bid, demo_mode=demo_mode, move_cursor=True)
    elem.click(button=button, modifiers=modifiers, force=False, timeout=3000)


def make_action_set(subsets=('bid', 'coord', 'nav', 'tab', 'chat'), **kwargs):
    """Keep upstream actions except BID click; never mutate upstream registries.

    The click deadline covers actionability and navigation together. Coordinate
    and agent-browser actions retain their own backend semantics.
    """
    if kwargs.get('retry_with_force', False):
        raise ValueError('ScamWorld does not allow forced action retries')
    selected = []
    for subset in ([subsets] if isinstance(subsets, str) else subsets):
        if subset not in ACTION_SUBSETS:
            raise ValueError(f'Unsupported ScamWorld action subset: {subset}')
        selected.extend(click if f.__name__ == 'click' else f for f in ACTION_SUBSETS[subset])
    return HighLevelActionSet(subsets=['custom'], custom_actions=list(dict.fromkeys(selected)), **kwargs)
