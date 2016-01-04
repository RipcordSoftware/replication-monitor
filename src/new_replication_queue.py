import threading
import time
from queue import Queue


class NewReplicationQueue:
    class _QueueItem:
        def __init__(self, repl, done=None, err=None):
            self._repl = repl
            self._done = done
            self._err = err

        @property
        def repl(self):
            return self._repl

        @property
        def done(self):
            return self._done

        @property
        def err(self):
            return self._err

    def __init__(self, report_error=None):
        self._report_error = report_error
        self._queue = Queue()
        self._thread = threading.Thread(target=self._queue_worker)
        self._thread.daemon = True
        self._thread.start()

    def put(self, repl, done=None, err=None):
        self._queue.put(self._QueueItem(repl, done, err))

    def _queue_worker(self):
        while True:
            time.sleep(2)
            while not self._queue.empty():
                try:
                    item = self._queue.get(block=False)
                    item.repl.replicate()
                    if item.done:
                        item.done()
                except Exception as ex:
                    if item.err:
                        item.err(ex)
                    elif self._report_error:
                        self._report_error(ex)

