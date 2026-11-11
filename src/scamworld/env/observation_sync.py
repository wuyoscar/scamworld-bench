"""Bounded retries of observation reads, never of browser actions."""
from copy import deepcopy

from playwright.sync_api import Error as PlaywrightError


class ObservationDocumentChanged(RuntimeError):
    """A navigation crossed the screenshot/DOM/state capture boundary."""


def document_identity(page):
    # A same-URL reload still has a different time origin. No DOM mutation.
    return page.evaluate('() => ({url: location.href, time_origin: performance.timeOrigin})')


def require_document_identity(runtime, expected, stage):
    """Reject and persist a failed read instead of saving cross-page evidence."""
    if not expected:
        return
    try:
        if document_identity(runtime.page) != expected:
            raise ObservationDocumentChanged('Document changed during ' + stage)
    except (PlaywrightError, ObservationDocumentChanged) as error:
        runtime.environment_errors.append({'type': 'observation_document_error', 'stage': stage, 'message': str(error)})
        runtime._save()
        raise


def observe_stable_document(runtime, attempts, *, max_attempts=3, ready_timeout=5000):
    """Return one consistent observation and its already captured state.

    Events already drained into runtime.events remain there across read retries.
    Partially appended observations are rolled back; the action and its error
    are owned by the caller and are never repeated or changed here.
    """
    if not 1 <= max_attempts <= 3:
        raise ValueError('Observation reads allow one to three attempts')
    for number in range(1, max_attempts + 1):
        count = len(runtime.observations)
        attempt = {'attempt': number}
        attempts.append(attempt)
        reading = False
        try:
            runtime.page.wait_for_load_state('domcontentloaded', timeout=ready_timeout)
            before = document_identity(runtime.page)
            attempt['document_before'] = before
            reading = True
            runtime.observation_events_received = False
            public = runtime.observe()
            after = document_identity(runtime.page)
            attempt['document_after'] = after
            record = runtime.observations[-1]
            if (len(runtime.observations) != count + 1 or before != after or
                    record['url'] != after['url'] or record['state']['url'] != after['url']):
                raise ObservationDocumentChanged('Document changed while capturing observation')
            record['document_identity'] = after
            attempt['status'] = 'captured'
            record['observation_read_attempts'] = deepcopy(attempts)
            return public, deepcopy(record['state'])
        except (PlaywrightError, ObservationDocumentChanged) as error:
            # Do not turn a closed page/browser, arbitrary JS error, readiness
            # timeout or unknown Playwright failure into a successful empty read.
            transient = isinstance(error, ObservationDocumentChanged) or (
                isinstance(error, PlaywrightError) and
                'Execution context was destroyed' in str(error)
            )
            uncertain_event_delivery = reading and not getattr(runtime, 'observation_events_received', False)
            if uncertain_event_delivery:
                transient = False
                attempt['event_delivery'] = 'unknown_destructive_drain_not_retried'
            attempt.update(status='retry' if transient and number < max_attempts else 'failed',
                           error=str(error))
            del runtime.observations[count:]
            if attempt['status'] == 'failed':
                runtime.environment_errors.append({'type': 'observation_read_failed', 'message': str(error),
                                                   'event_delivery': attempt.get('event_delivery', 'previous_events_preserved')})
            runtime._save()
            if not transient or number == max_attempts:
                raise
    raise AssertionError('Unreachable observation retry state')
