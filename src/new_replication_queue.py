from queue import Queue

class NewReplicationQueue:
    def __init__(self, couchdb):
        self._couchdb = couchdb
        self._queue = Queue()

    def queue_replication(self, repl):
        self._queue.put(repl)
