from __future__ import annotations

import time
from PySide6.QtCore import QEventLoop
from oh_my_ruyi.app.task_runner import BaseTask, TaskRunner


def _wait_for_signal(signal, timeout_ms: int = 2000) -> list:
    results = []
    loop = QEventLoop()

    def _handler(*args):
        results.extend(args)
        loop.quit()

    signal.connect(_handler)
    # Wait or process events
    loop.exec()
    return results


def test_base_task_success(qtbot) -> None:
    def _sample_fn(a: int, b: int) -> int:
        return a + b

    task = BaseTask(_sample_fn, 5, 7)
    results = []
    task.signals.finished.connect(results.append)

    task.run()
    assert results == [12]


def test_base_task_error(qtbot) -> None:
    def _failing_fn() -> None:
        raise ValueError("Something went wrong")

    task = BaseTask(_failing_fn)
    errors = []
    task.signals.error.connect(errors.append)

    task.run()
    assert len(errors) == 1
    assert "ValueError: Something went wrong" in errors[0]


def test_base_task_cancellation() -> None:
    ran = []

    def _fn() -> None:
        ran.append(True)

    task = BaseTask(_fn)
    task.cancel()
    assert task.is_cancelled

    results = []
    task.signals.finished.connect(results.append)
    task.run()

    assert ran == []
    assert results == []


def test_task_runner_submit_and_cancel_all(qtbot) -> None:
    runner = TaskRunner()

    def _slow_fn() -> str:
        time.sleep(0.1)
        return "done"

    task = BaseTask(_slow_fn)
    runner.submit(task)

    assert task in runner.active_tasks

    # Wait for completion
    with qtbot.waitSignal(task.signals.finished, timeout=3000) as blocker:
        pass

    assert blocker.args == ["done"]
    # Task should be removed from active_tasks when finished
    assert task not in runner.active_tasks


def test_task_runner_cancel_all() -> None:
    runner = TaskRunner()

    def _fn() -> None:
        pass

    task1 = BaseTask(_fn)
    task2 = BaseTask(_fn)
    runner.active_tasks.extend([task1, task2])

    runner.cancel_all()
    assert task1.is_cancelled
    assert task2.is_cancelled
