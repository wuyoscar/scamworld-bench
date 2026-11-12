"""BrowserGym task adapter; no score is invented when an evaluator is absent.

BrowserGym performs actions; validate snapshots the actual post-action page and
collects trusted local events. Its action text comes from the environment log,
while DOM click/input callbacks establish actual dispatch independently.
"""
from __future__ import annotations

import json
import logging
import os
import ast
import shutil
import time
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import Error as PlaywrightError
from browsergym.core import observation as bg_observation
from browsergym.core.env import EXTRACT_OBS_MAX_TRIES
from browsergym.core.observation import MarkingError
from browsergym.core.task import AbstractBrowserTask
from browsergym.core.env import BrowserEnv
from browsergym.core.spaces import Unicode
from gymnasium import spaces
from .runtime import BrowserRuntime, open_start_page, settle_animations
from . import offsite
from scamworld.agents.interface_v11 import guard_browsergym_call
from .action_errors import SETTLE_SECONDS, SIGNATURE_JS, action_signals, classify_action_error, navigation_pending
from .input_values import rewrite_fill_action
from .observation_sync import document_identity, observe_stable_document, require_document_identity
from .bgym_persistent import install as install_persistent_context


class _FixedSettingNotice(logging.Filter):
    """BrowserGym logs a warning each time the environment applies the viewport and the timeout that every task runs with.
    They are fixed settings of the environment, not a problem of the user's set-up, so that one message is dropped."""
    def filter(self, record):
        return not str(record.msg).startswith("Overriding the task's ")


logging.getLogger('browsergym.core.env').addFilter(_FixedSettingNotice())


class ScamWorldBrowserTask(AbstractBrowserTask):
    @classmethod
    def get_task_id(cls):
        return "scamworld"

    def __init__(self, seed: int, *, site_dir, artifact_dir, case_id, goal,
                 case=None, evaluator=None, start_path="/index.html"):
        super().__init__(seed)
        self.slow_mo = 0
        self.goal, self.case, self.evaluator = goal, case, evaluator
        self.runtime = BrowserRuntime(site_dir, artifact_dir, case_id=case_id, start_path=start_path)
        self.runtime.seed = seed
        self.runtime.episode_id = 1
        self.previous_state = None
        self.last_chat_length = 0
        self.pending_action = None
        self.pending_normalized_action = None
        self.execution_error_reader = None

    def setup(self, page):
        self.runtime.attach(page)
        self.runtime.start_page_wait = open_start_page(page, self.runtime.server.origin + self.runtime.start_path)
        _,self.previous_state = observe_stable_document(self.runtime, [])
        # Goal is authored public task text; no case/evaluation fields returned.
        return self.goal, {"case_id":self.runtime.case_id,"network_policy":"owned_loopback_origin_only"}

    def validate(self, page, chat_messages):
        self.runtime.page=page
        pending=chat_messages[self.last_chat_length:]
        self.last_chat_length=len(chat_messages)
        answer_messages=[m for m in pending if m.get("role")=="assistant"]
        action=self.pending_normalized_action or ({"type":"browsergym_action","value":self.pending_action} if self.pending_action is not None else {"type":"browsergym_observation"})
        if answer_messages and getattr(self,"final_reply","structured")!="message":   # a11: FormalBrowserTask recorded the message
            raw=answer_messages[-1].get("message","")
            try:
                final=json.loads(raw)
                if isinstance(final,dict) and "fields" in final:
                    self.runtime.final_answer=final
                    self.runtime.terminated=True
                    action={"type":"final_answer","value":final}
            except (TypeError,json.JSONDecodeError): pass
        # BrowserGym does not pass its action string into task.validate. Preserve
        # this distinction instead of reconstructing an attempted action from DOM.
        entry={"step":len(self.runtime.actions)+1,"proposed_action":action,"executed_action":None,
               "state_before":self.previous_state,"error":None,"status":"not_executed"}
        if self.pending_action is not None and self.execution_error_reader:
            error=self.execution_error_reader()
            entry.update(status='failed' if error else 'executed',error=error or None,
                         executed_action=None if error else action)
        self.runtime.actions.append(entry)
        first_event=len(self.runtime.events)
        entry['observation_read_attempts']=[]
        obs,after=observe_stable_document(self.runtime,entry['observation_read_attempts'])
        entry.update(state_after=after,transition_observed=self.previous_state!=after,
                     observation_id=obs["observation_id"],events=self.runtime.events[first_event:])
        self.previous_state=after
        self.runtime._save()
        info={"trace_path":str(self.runtime.artifact_dir/'trace.json'),"scoring_status":"pending_evaluator"}
        reward=0.0
        if self.runtime.terminated and self.evaluator:
            result=self.evaluator(self.case,self.runtime.export_trace())
            info.update(scoring_status="evaluated",evaluation=result)
            reward=step_reward(result)
        return reward,self.runtime.terminated,"",info

    def teardown(self):
        # BrowserGym owns browser/context; runtime only owns the local server. BrowserEnv closes the context right after
        # this: the route handler goes first (runtime.detach), before the server its fetches read from.
        self.runtime.detach()
        self.runtime.server.close()


def configure_local_chrome(cache_dir):
    """Make Playwright find a local Chromium for BrowserGym's chat window, which has no executable_path option.

    BrowserGym 0.14 launches the Chromium build that its Playwright version pins (chromium-1117). When Playwright's macOS
    cache folder (~/Library/Caches/ms-playwright) holds chromium-1187, this links the pinned location in `cache_dir` to
    it and points PLAYWRIGHT_BROWSERS_PATH at `cache_dir`; nothing is downloaded and the default cache is not changed.
    When only the pinned build is installed there is nothing to do; when neither is, FileNotFoundError says how to
    install it."""
    cache=Path(cache_dir).resolve()
    source=Path.home()/'Library/Caches/ms-playwright/chromium-1187/chrome-mac'
    if not (source/'Chromium.app/Contents/MacOS/Chromium').exists():
        if (Path(os.environ.get('PLAYWRIGHT_BROWSERS_PATH') or Path.home()/'Library/Caches/ms-playwright')/'chromium-1117').is_dir():
            return   # Playwright's own Chromium for this version (`playwright install chromium`): nothing to alias
        raise FileNotFoundError('No Chromium for BrowserGym chat: run `uv run playwright install chromium` (no browser was downloaded)')
    alias=cache/'chromium-1117/chrome-mac'
    alias.parent.mkdir(parents=True,exist_ok=True)
    if alias.is_dir() and not alias.is_symlink():shutil.rmtree(alias)
    if not alias.exists():alias.symlink_to(source,target_is_directory=True)
    os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(cache)


class ScamWorldBrowserEnv(BrowserEnv):
    """Capture the actual proposed BrowserGym action and its execution error."""
    def __init__(self,*args,observation_track='screenshot',**kwargs):
        if observation_track not in ('screenshot','accessibility'):
            raise ValueError('Observation track must be screenshot or accessibility')
        if kwargs.get('use_raw_page_output'):
            raise ValueError('Raw browser pages are evaluator-only')
        self.observation_track=observation_track
        self._raw_action_error,self._before_action='',None   # raw text of the last action error; page signature before it
        install_persistent_context()  # a non-persistent context costs the macOS secd daemon ~9 CPU-s per browser
        super().__init__(*args,**kwargs)
        public_spaces=dict(self.observation_space.spaces)
        # Accessibility observations retain DOM for the explicit HTML profile.
        if observation_track=='screenshot':public_spaces.pop('dom_object',None)
        if observation_track=='screenshot':
            for key in ('axtree_object','extra_element_properties','focused_element_bid'):public_spaces.pop(key,None)
        public_spaces.update(step_id=spaces.Discrete(2**31),observation_id=Unicode(),screenshot_path=Unicode(),observation_track=Unicode())
        self.observation_space=spaces.Dict(public_spaces)

    def reset(self,*args,**kwargs):
        obs,info=super().reset(*args,**kwargs)
        # BrowserGym's own greeting ("Hi! I am your UI assistant ...", role assistant) and the goal are in the chat after the
        # reset; only messages sent after it are the agent's (under a11 an assistant message ends the episode).
        self.task.last_chat_length=len(self.chat.messages)
        return obs,info

    def _task_validate(self):
        out=super()._task_validate()
        if getattr(self.task,'offsite_notice',False):   # a11: an off-site link reads as an unreachable site (FormalBrowserTask.validate)
            from scamworld.env.action_errors import UNREACHABLE
            self.last_action_error=UNREACHABLE
        return out

    def _get_obs(self):
        # Core 0.14.3's CDP screenshot override/detach changes the live viewport
        # on the locally installed Chromium. Reuse the task's recorded PNG;
        # never resize the page or invoke that capture branch to produce input.
        # Coordinate actions divide by this factor, so unsupported scaling must
        # fail explicitly rather than return an image in a different space.
        if getattr(self.page,'_bgym_scale_factor',1.0)!=1.0:
            raise ValueError('ScamWorld BrowserGym observations require scale_factor=1')
        last=self.task.runtime.observations[-1]
        with Image.open(last['screenshot_path']) as saved:
            screenshot=np.asarray(saved.convert('RGB')).copy()
        geometry=self.page.evaluate('() => [innerWidth, innerHeight]')
        if geometry != [screenshot.shape[1],screenshot.shape[0]]:
            raise RuntimeError('Recorded screenshot dimensions differ from the live action viewport')

        # Reuse BrowserGym's metadata-only branch internally. The live page is
        # removed before returning; callers still cannot request raw page output.
        original_raw=self.use_raw_page_output
        self.use_raw_page_output=True
        try:
            obs=super()._get_obs()
        finally:
            self.use_raw_page_output=original_raw
        obs.pop('page',None)

        # Mark bids for the existing finite ID action API on both tracks. Keep
        # core's bounded detached-frame retries, with cleanup on every outcome.
        # These helpers are imported, not vendored or globally monkeypatched.
        retry_messages=('Frame was detached','Frame with the given frameId is not found',
                        'Execution context was destroyed','Frame has been detached',
                        'Cannot mark a child frame without a bid','Cannot read properties of undefined')
        for retries_left in reversed(range(EXTRACT_OBS_MAX_TRIES)):
            try:
                bg_observation._pre_extract(self.page,tags_to_mark=self.tags_to_mark,lenient=retries_left==0)
                if self.observation_track=='accessibility':
                    dom=bg_observation.extract_dom_snapshot(self.page)
                    obs.update(dom_object=dom,axtree_object=bg_observation.extract_merged_axtree(self.page),
                               focused_element_bid=bg_observation.extract_focused_element_bid(self.page),
                               extra_element_properties=bg_observation.extract_dom_extra_properties(dom,scale_factor=1.0))
            except (PlaywrightError,MarkingError) as error:
                if retries_left==0 or not any(message in str(error) for message in retry_messages):
                    raise
            else:
                break
            finally:
                bg_observation._post_extract(self.page)
            time.sleep(0.5)
        if self.page.evaluate('() => [innerWidth, innerHeight]') != geometry:
            raise RuntimeError('Observation extraction changed the live action viewport')
        if self.observation_track=='accessibility':
            # Compare only the exact supplied AX projection; node IDs and pixels
            # are not content changes. Keep actual dispatch separate from change.
            projection=[{'role':n.get('role',{}).get('value'),
                         'name':n.get('name',{}).get('value',''),
                         'value':n.get('value',{}).get('value')}
                        for n in obs.get('axtree_object',{}).get('nodes',[]) if not n.get('ignored')]
            previous=getattr(self.task,'previous_public_ax',None)
            if self.task.runtime.actions:
                entry=self.task.runtime.actions[-1]
                entry['public_observation_changed']=previous is not None and previous!=projection
                entry['transition_observed']=entry['transition_observed'] or entry['public_observation_changed']
            self.task.previous_public_ax=projection
        # Contract-2 cases never opted in, leaving agents unable to set native dropdowns. Expose observed
        # native selects by default; SCAMWORLD_NATIVE_SELECT=0 restores the opt-in-only behaviour.
        if getattr(self.task,'case',None) and (self.task.case['task'].get('observed_select_version')=='1' or os.environ.get('SCAMWORLD_NATIVE_SELECT','1')!='0'):
            observed={n.get('browsergym_id') for n in obs.get('axtree_object',{}).get('nodes',[]) if not n.get('ignored') and n.get('role',{}).get('value')=='combobox'}
            actual=self.page.evaluate("""() => Array.from(document.querySelectorAll('select[bid]')).map(e=>({bid:e.getAttribute('bid'),disabled:e.disabled,multiple:e.multiple,options:Array.from(e.options).map(o=>({label:o.label,value:o.value,disabled:o.disabled||!!(o.parentElement.tagName==='OPTGROUP'&&o.parentElement.disabled)}))}))""")
            obs['observed_native_selects']={r['bid']:{k:v for k,v in r.items() if k!='bid'} for r in actual if r['bid'] in observed}
        obs.update(screenshot=screenshot,step_id=len(self.task.runtime.actions),
                   observation_id=last['observation_id'],screenshot_path=last['screenshot_path'],
                   observation_track=self.observation_track)
        require_document_identity(self.task.runtime,last.get('document_identity'),'screenshot and accessibility extraction')
        return obs

    def _input_type_of_bid(self,bid):
        """The type of the <input> a fill targets (date, month, time, datetime-local take one machine form), else None."""
        try:
            locator=self.page.locator('[bid='+json.dumps(str(bid))+']')
            return locator.evaluate("e => e.tagName === 'INPUT' ? e.type : null",timeout=500) if locator.count()==1 else None
        except PlaywrightError:return None

    def _action_signature(self):
        try:return self.page.evaluate(SIGNATURE_JS)|{'pages':len(self.context.pages)}
        except PlaywrightError:return None

    def _settle(self,raw):
        """Let the page finish loading (bounded) before it is observed. After an action that raised, the guard events of
        the current page are carried over first (a navigation may replace it at any moment, and the step keeps them);
        a click whose scheduled navigation was still pending is waited for until the document is replaced."""
        end=time.monotonic()+SETTLE_SECONDS
        old=(self._before_action or {}).get('doc')
        if old and raw:
            try:
                runtime=self.task.runtime
                if runtime._allowed(self.page.url) and document_identity(self.page)==old:
                    url=self.page.url
                    runtime.carried_events+=[{**e,'url_observed':url} for e in self.page.evaluate('window.__pagekitDrainEvents ? window.__pagekitDrainEvents() : []')]
                    runtime.carried_events+=[{**e,'url_observed':url,'source':'site_instrumentation'}
                                             for e in self.page.evaluate('window.__pagekitDrainSiteEvents ? window.__pagekitDrainSiteEvents() : []')]
                while navigation_pending(raw) and time.monotonic()<end and document_identity(self.page)==old:
                    self.page.wait_for_timeout(100)
            except PlaywrightError:pass   # the old context was destroyed: the navigation committed
        for page in list(self.context.pages):
            left=end-time.monotonic()
            if left<=0:break
            try:page.wait_for_load_state('domcontentloaded',timeout=max(1,int(left*1000)))   # timeout=0 would wait forever
            except PlaywrightError:pass   # navigation in flight or still loading: the observation retries
        settle_animations(self.page)   # entrance animations with delays finish first (3 s cap, never fails the step)

    def post_step(self,info,validate=True):
        """BrowserGym has set last_action_error from the raw exception. Settle the page, then tell the agent about real
        failures only (neutral words); the raw text stays on the environment and goes to the trace."""
        raw=self._raw_action_error=self.last_action_error
        self._settle(raw)
        if raw:
            message,_=classify_action_error(raw,**action_signals(self._before_action,self._action_signature()))
            self.last_action_error=message or ''
        return super().post_step(info,validate)

    def _back_to_blank(self):
        """True when the entry before the current one is the tab's initial about:blank (the start page's own history)."""
        try:
            cdp=self.page.context.new_cdp_session(self.page)
            try:hist=cdp.send('Page.getNavigationHistory')
            finally:cdp.detach()
        except Exception:
            return False
        i=hist.get('currentIndex',0);entries=hist.get('entries') or []
        return i==1 and len(entries)>1 and entries[0].get('url')=='about:blank'

    def step(self,action):
        self._raw_action_error=''
        self._before_action=self._action_signature()
        self.task.pending_action=action
        self.task.pending_normalized_action=None
        self.task.execution_error_reader=lambda:self.last_action_error
        original_mapping=self.action_mapping
        allowed={'click','hover','press','keyboard_press','mouse_click','fill','select_option','scroll','go_back','go_forward','goto','tab_focus','new_tab','tab_close','send_msg_to_user','noop',
                 'keyboard_type','mouse_move'}   # BrowserGym coord type / hover (screenshot condition)
        def guarded_mapping(text):
            tree=ast.parse(text)
            for node in tree.body:
                if not isinstance(node,ast.Expr) or not isinstance(node.value,ast.Call) or not isinstance(node.value.func,ast.Name) or node.value.func.id not in allowed:
                    raise ValueError('Unsupported ScamWorld BrowserGym action')
                call=node.value
                args=[ast.literal_eval(a) for a in call.args]
                for kw in call.keywords:ast.literal_eval(kw.value)
                guard_browsergym_call(call.func.id,args,call.keywords)
                if call.func.id in ('goto','new_tab') and args and not self.task.runtime._allowed(args[0]):
                    self.task.runtime.events.append({'type':'boundary_attempt','url':args[0],'transport':'browsergym_action','blocked':True,'step':len(self.task.runtime.actions)+1})
                    # Outside the offsite condition a goto to another site opens, as in a
                    # browser without network, the unreachable page (runtime._refuse), instead of being refused before it runs
                    if offsite.on() or call.func.id!='goto':
                        raise ValueError(offsite.BLOCKED_ERROR if offsite.on() else 'Only the owned loopback origin is allowed')
                if call.func.id=='tab_close' and len(self.page.context.pages)<=1:
                    raise ValueError('Only one tab is open')
                if call.func.id=='tab_focus' and args and not 0<=args[0]<len(self.page.context.pages):
                    raise ValueError('No tab with that index')
                if call.func.id=='go_back' and len(tree.body)==1 and self._back_to_blank():
                    # The tab was about:blank before BrowserGym opened the start page, so going back from the
                    # start page would show an empty page; a browser that opened the site has nothing to go back to
                    self.task.pending_normalized_action={'type':'back','raw_browsergym_action':text,'no_history':True}
                    return original_mapping('noop(0)')
                if len(tree.body)==1:
                    names={'fill':'type_fixture_text','go_back':'back','go_forward':'forward','goto':'open_local_url','tab_focus':'switch_tab','mouse_click':'click_coordinate','keyboard_type':'type_text','mouse_move':'hover_coordinate'}
                    normalized={'type':names.get(call.func.id,call.func.id),'raw_browsergym_action':text}
                    if call.func.id in ('click','hover','fill','select_option','press') and args:
                        locator=self.page.locator('[bid='+json.dumps(str(args[0]))+']')
                        if locator.count()==1:
                            normalized['target']=locator.get_attribute('data-action-id') or locator.get_attribute('id')
                            normalized['observed_bid']=str(args[0])
                        if len(args)>1:normalized['value']=args[1]
                        if call.func.id=='fill':normalized['input_semantics']='free_form_text'
                    elif call.func.id=='mouse_move' and len(args)>=2:
                        normalized.update(x=args[0],y=args[1],raw_type='mouse_move')
                    elif call.func.id=='mouse_click' and len(args)>=2:
                        normalized.update(x=args[0],y=args[1],raw_type='mouse_click')
                        target=self.task.runtime.target_at_point(args[0],args[1])
                        if target:normalized.update(type='click',target=target)
                    elif args:normalized['value']=args[0] if len(args)==1 else args
                    self.task.pending_normalized_action=normalized
            # Text typed into a date / month / time / datetime-local input in the form the page displays (18.07.2026) is
            # entered in the form the control takes (2026-07-18) when it has one reading; the agent's own text stays in `value`
            text,changed=rewrite_fill_action(text,self._input_type_of_bid)
            if changed and self.task.pending_normalized_action is not None:self.task.pending_normalized_action['value_entered']=changed[0][2]
            return original_mapping(text)
        self.action_mapping=guarded_mapping
        try:result=super().step(action)
        finally:self.action_mapping=original_mapping
        error=result[0].get('last_action_error','')
        entry=self.task.runtime.actions[-1]
        entry.update(status='failed' if error else 'executed',error=error or None,
                     executed_action=None if error else {"type":"browsergym_action","value":action})
        if self._raw_action_error:entry['raw_action_error']=self._raw_action_error
        self.task.pending_action=None
        self.task.pending_normalized_action=None
        self.task.runtime._save()
        return result


def step_reward(result):
    """BrowserGym step reward of an evaluation. Reward must be explicitly declared by the integrated evaluator.
    FormalBrowserTask's evaluator is scoring/outcome.evaluate_episode, whose `overall` is the outcome of `scamworld score`
    (benign logic on a legitimate task); an evaluator without it (the structured-answer checks) keeps validity x goal."""
    if "overall" in result:
        return float(result["overall"])
    return float(result.get("run_validity",{}).get("status")=="valid" and result.get("task_goal",{}).get("status")=="met")
