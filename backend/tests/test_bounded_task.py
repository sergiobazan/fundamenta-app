import multiprocessing
import os
import time

import pytest
from app.bounded_task import run_bounded


def test_returns_serializable_result():
    assert run_bounded(sum, ([2, 3],), 5) == 5


def test_propagates_child_error():
    with pytest.raises(RuntimeError, match="ValueError"):
        run_bounded(int, ("invalid",), 5)


def test_timeout_terminates_process_without_leaking_worker():
    before = {p.pid for p in multiprocessing.active_children()}
    with pytest.raises(TimeoutError):
        run_bounded(time.sleep, (20,), 0.1)
    assert {p.pid for p in multiprocessing.active_children()} == before


def test_child_crash_does_not_leave_job_waiting():
    with pytest.raises(RuntimeError, match="sin devolver resultado"):
        run_bounded(os._exit, (1,), 5)
