"""Persisted provider dispatch budgets shared by all stages of one operation."""
import json
import time
from copy import copy
from .cancellation import check_cancelled
from .research_scope import _write, _json


class BudgetExceeded(BaseException):
    """Bypass retries; callers may publish explicitly partial, accepted work."""


class BudgetProvider:
    def __init__(self, provider, path, *, calls=6, characters=144_000, seconds=480):
        if any(type(v) is not int or v <= 0 for v in (calls, characters, seconds)):
            raise ValueError('Operation budgets must be positive integers.')
        self.delegate, self.path = provider, path
        self.name = getattr(provider, 'name', 'configured_provider')
        self.started = time.monotonic()
        self.state = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {
            'calls': 0, 'characters': 0, 'elapsed_seconds': 0,
            'limits': {'calls': calls, 'characters': characters, 'seconds': seconds}}
        # Existing operation limits cannot grow implicitly on resume.
        self.limits = {k: min(self.state['limits'][k], v) for k, v in
                       {'calls': calls, 'characters': characters, 'seconds': seconds}.items()}
        self.elapsed_before = self.state['elapsed_seconds']

    def save(self):
        self.state['elapsed_seconds'] = self.elapsed_before + time.monotonic() - self.started
        self.state['limits'] = self.limits
        _write(self.path, _json(self.state))

    def check_available(self, prompt):
        check_cancelled()
        remaining = self.limits['seconds'] - self.elapsed_before - (time.monotonic() - self.started)
        if (self.state['calls'] >= self.limits['calls'] or
                self.state['characters'] + len(prompt) > self.limits['characters'] or remaining < 1):
            self.save()
            raise BudgetExceeded('Operation stopped at its budget. Accepted work is saved; no further calls were dispatched.')
        return remaining

    def generate(self, prompt, **kwargs):
        remaining = self.check_available(prompt)
        self.state['calls'] += 1
        self.state['characters'] += len(prompt)
        # Reserve the full remaining timeout before dispatch so interruption of
        # the host cannot silently refill a time allowance on a later resume.
        self.state['elapsed_seconds'] = self.limits['seconds']
        _write(self.path, _json(self.state))
        delegate = self.delegate
        if hasattr(delegate, 'timeout_seconds'):
            delegate = copy(delegate)
            delegate.timeout_seconds = min(delegate.timeout_seconds, max(1, int(remaining)), 120)
        try:
            result = delegate.generate(prompt, **kwargs)
            check_cancelled()
            if time.monotonic() - self.started + self.elapsed_before > self.limits['seconds']:
                raise BudgetExceeded('The operation time budget was reached; the result was not published as complete.')
            return result
        finally:
            self.save()
