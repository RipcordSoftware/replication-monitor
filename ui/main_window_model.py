from threading import local
from collections import namedtuple

from src.couchdb import CouchDB


class MainWindowModel:
    def __init__(self, server, port, secure, get_credentials=None):
        self._server = server
        self._port = port
        self._secure = secure
        self._get_credentials = get_credentials
        self._local = local()
        self._local.couchdb = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        if self._local.couchdb:
            self._local.couchdb.close()
            self._local.couchdb = None

    # TODO: remove this
    @property
    def couchdb(self):
        return self._couchdb

    # TODO: review
    @property
    def url(self):
        return self._couchdb.get_url()

    @property
    def session(self):
        return self._couchdb.get_session()

    @property
    def databases(self):
        databases = []
        for db_name in self._couchdb.get_databases():
            db = self._couchdb.get_database(db_name)
            limit = self._couchdb.get_revs_limit(db_name)
            db = self._append_field(db, ('revs_limit', limit), 'Database')
            databases.append(db)
        return databases

    @property
    def replication_tasks(self):
        tasks = self._couchdb.get_active_tasks('replication')
        return tasks

    @property
    def signature(self):
        signature = self._couchdb.get_signature()
        return signature

    @property
    def database_type(self):
        return self._couchdb.db_type

    @property
    def session(self):
        return self._couchdb.get_session()

    def create_database(self, name):
        self._couchdb.create_database(name)

    def get_database(self, name):
        return self._couchdb.get_database(name)

    def delete_database(self, name):
        self._couchdb.delete_database(name)

    def compact_database(self, name):
        self._couchdb.compact_database(name)

    def set_revs_limit(self, name, limit):
        self._couchdb.set_revs_limit(name, limit)

    @property
    def _couchdb(self):
        couchdb = None
        try:
            couchdb = self._local.couchdb
        except AttributeError:
            pass

        if not couchdb:
            couchdb = CouchDB(self._server, self._port, self._secure, self._get_credentials)
            self._local.couchdb = couchdb

        return couchdb

    @staticmethod
    def _append_field(source, field, name='NewType'):
        fields = [key for key in source._fields]
        fields.append(field[0])
        NewType = namedtuple(name, fields)
        values = [value for value in iter(source)]
        values.append(field[1])
        return NewType(*values)
