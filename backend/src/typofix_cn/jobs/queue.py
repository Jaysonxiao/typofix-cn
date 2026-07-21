from typing import Optional
import queue
import threading
from collections.abc import Callable


class JobQueue:
    def __init__(self, *, worker: Callable[[object], None]) -> None:
        self._worker = worker
        self._items: queue.Queue[Optional[object]] = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._stopped = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stopped.clear()
        self._thread = threading.Thread(target=self._run, name="typofix-job-worker", daemon=True)
        self._thread.start()

    def submit(self, item: object) -> None:
        self._items.put(item)

    def stop(self) -> None:
        self._stopped.set()
        self._items.put(None)
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stopped.is_set():
            item = self._items.get()
            try:
                if item is None:
                    return
                self._worker(item)
            finally:
                self._items.task_done()
