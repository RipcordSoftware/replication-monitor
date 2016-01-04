from enum import Enum
from urllib.parse import urlparse

from src.couchdb import CouchDB


class Replication:
    class ReplType(Enum):
        All = 1
        Docs = 2
        Designs = 3

    def __init__(self, couchdb, source, target, continuous=False, create=False, drop_first=False, repl_type=ReplType.All):
        self._couchdb = couchdb
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

    def replicate(self):
        # asking for the replicator database will force the user to give the right auth credentials
        self._couchdb.get_database('_replicator')

        if Replication._is_local(self._source) and Replication._is_local(self._target):
            return self._replicate_local()
        else:
            return self._replicate_remote()

    def _replicate_local(self):
        source_name = self._source
        target_name = self._target

        if self._couchdb.db_type is CouchDB.DatabaseType.Cloudant and self._couchdb.auth:
            url = self._couchdb.get_url()
            url = url.replace('://', '://' + self._couchdb.auth.url_auth + '@')
            source = url + source_name
            target = url + target_name
        else:
            source = source_name
            target = target_name

        if self._drop_first:
            try:
                self._couchdb.delete_database(target_name)
            except:
                pass
            if not self._create:
                self._couchdb.create_database(target_name)

        return self._couchdb.create_replication(source, target, create_target=self._create, continuous=self._continuous)

    def _replicate_remote(self):
        source = self._source
        target = self._target
        source_is_remote = not self._is_local(source)
        target_is_remote = not self._is_local(target)

        if source_is_remote:
            source_couchdb = self._get_couchdb_from_url(source, self._couchdb.get_credentials_callback)
        else:
            source_couchdb = self._couchdb

        if target_is_remote:
            target_couchdb = self._get_couchdb_from_url(target, self._couchdb.get_credentials_callback)
            target_name = self._get_database_from_url(target)
        else:
            target_couchdb = self._couchdb

        # asking for the replicator database will force the user to give the right auth credentials
        source_couchdb.get_docs('_replicator', limit=0)
        target_couchdb.get_docs('_replicator', limit=0)

        if source_is_remote and source_couchdb.auth:
            source = source.replace('://', '://' + source_couchdb.auth.url_auth + '@')

        if target_is_remote and target_couchdb.auth:
            target = target.replace('://', '://' + target_couchdb.auth.url_auth + '@')

        if self._drop_first:
            try:
                target_couchdb.delete_database(target_name)
            except:
                pass
            if not self._create:
                target_couchdb.create_database(target_name)

        return self._couchdb.create_replication(source, target, create_target=self._create, continuous=self._continuous)

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
