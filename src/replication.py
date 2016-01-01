from enum import Enum
from urllib.parse import urlparse

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
        # asking for the replicator database will force the user to give the right auth credentials
        couchdb.get_database('_replicator')

        if Replication._is_local(self._source) and Replication._is_local(self._target):
            return self._replicate_local(couchdb)
        else:
            return self._replicate_remote(couchdb)

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

    def _replicate_remote(self, couchdb):
        source = self._source
        target = self._target
        source_is_remote = not self._is_local(source)
        target_is_remote = not self._is_local(target)

        if source_is_remote:
            source_couchdb = self._get_couchdb_from_url(source, couchdb.get_credentials_callback)
            source_name = self._get_database_from_url(source)
        else:
            source_couchdb = couchdb

        if target_is_remote:
            target_couchdb = self._get_couchdb_from_url(target, couchdb.get_credentials_callback)
            target_name = self._get_database_from_url(target)
        else:
            target_couchdb = couchdb

        # asking for the replicator database will force the user to give the right auth credentials
        source_couchdb.get_database('_replicator')
        target_couchdb.get_database('_replicator')

        if source_is_remote and source_couchdb.auth:
            headers = {'Authorization': 'Basic ' + source_couchdb.auth}
            source = {'url': source_couchdb.get_url() + source_name, 'headers': headers}

        if target_is_remote and target_couchdb.auth:
            headers = {'Authorization': 'Basic ' + target_couchdb.auth}
            target = {'url': target_couchdb.get_url() + target_name, 'headers': headers}

        if self._drop_first:
            try:
                target_couchdb.delete_database(target_name)
            except:
                pass
            if not self._create:
                target_couchdb.create_database(target_name)

        return couchdb.create_replication(source, target, create_target=self._create, continuous=self._continuous)

    @staticmethod
    def _is_local(db):
        return type(db) == str and not db.startswith('http')

    @staticmethod
    def _get_couchdb_from_url(url, get_credentials=None):
        u = urlparse(url)
        secure = u.scheme == 'https'
        port = u.port if u.port is not None else 443 if secure else 80
        return CouchDB(u.hostname, port, secure, get_credentials=get_credentials)

    @staticmethod
    def _get_database_from_url(url):
        u = urlparse(url)
        return u.path[1::]
