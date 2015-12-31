from enum import Enum

from src.couchdb import CouchDB


class Replication:
    class ReplType(Enum):
        All = 1
        Docs = 2
        Designs = 3

    def __init__(self, source, target, continuous=False, create=False, drop_first=False, repl_type=ReplType.All):
        self._source = source
        self._target = target
        self._continuous = continuous
        self._create = create
        self._drop_first = drop_first
        self._repl_type = repl_type

    @property
    def source(self):
        return self._source

    @property
    def target(self):
        return self._target

    @property
    def continuous(self):
        return self._continuous

    @property
    def create(self):
        return self._create

    @property
    def drop_first(self):
        return self._drop_first

    @property
    def repl_type(self):
        return self._repl_type

    def replicate(self, couchdb):
        if Replication._is_local(self._source) and Replication._is_local(self._target):
            return self._replicate_local(couchdb)

    def _replicate_local(self, couchdb):
        source_name = self._source
        target_name = self._target

        if couchdb.db_type is CouchDB.DatabaseType.Cloudant and couchdb.auth:
            headers = {'Authorization': 'Basic ' + couchdb.auth}
            source = {'url': couchdb.get_url() + source_name, 'headers': headers}
            target = {'url': couchdb.get_url() + target_name, 'headers': headers}
        else:
            source = source_name
            target = target_name

        if self._drop_first:
            try:
                couchdb.delete_database(target_name)
            except:
                pass
            if not self._create:
                couchdb.create_database(target_name)

        return couchdb.create_replication(source, target, create_target=self._create, continuous=self._continuous)

    @staticmethod
    def _is_local(db):
        return type(db) == str and not db.startswith('http')
