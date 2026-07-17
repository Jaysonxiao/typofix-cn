import threading
import time

from typofix_cn.jobs.queue import JobQueue


class ConcurrencyProbe:
    def __init__(self) -> None:
        self.active = 0
        self.max_concurrency = 0
        self.completed: list[str] = []
        self.lock = threading.Lock()

    def run(self, value: str) -> None:
        with self.lock:
            self.active += 1
            self.max_concurrency = max(self.max_concurrency, self.active)
        time.sleep(0.02)
        with self.lock:
            self.active -= 1
            self.completed.append(value)

    def wait_for_all(self) -> None:
        deadline = time.time() + 2
        while len(self.completed) < 2 and time.time() < deadline:
            time.sleep(0.01)


def test_queue_runs_only_one_analysis_at_a_time() -> None:
    probe = ConcurrencyProbe()
    queue = JobQueue(worker=probe.run)
    queue.start()
    queue.submit("a")
    queue.submit("b")
    probe.wait_for_all()
    queue.stop()
    assert probe.max_concurrency == 1
    assert probe.completed == ["a", "b"]
