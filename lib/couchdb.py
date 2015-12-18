import json
from collections import namedtuple
from http.client import HTTPConnection, HTTPSConnection
from base64 import b64encode


class CouchDBException(Exception):
    def __init__(self, response):
        self._response = response

    @property
    def status(self):
        return self._response.status

    @property
    def body(self):
        return self._response.body

    @property
    def content_type(self):
        return self._response.content_type

    @property
    def is_json(self):
        return self._response.is_json


class CouchDB:
    class Response:
        def __init__(self, status, body=None, content_type=None):
            self._status = status
            self._body = body
            self._content_type = content_type

        @property
        def status(self):
            return self._status

        @property
        def body(self):
            return self._body

        @property
        def content_type(self):
            return self._content_type

        @property
        def is_json(self):
            return self._content_type.find('application/json') == 0

    _auth = None
    _auth_active = False

    def __init__(self, host, port, secure, get_credentials=None):
        self._conn = HTTPSConnection(host, port) if secure else HTTPConnection(host, port)
        self._get_credentials = get_credentials

    def connect(self):
        response = self._make_request('/', 'HEAD')
        if response.status != 200:
            raise CouchDBException(response)
        else:
            return True

    def create_database(self, name):
        response = self._make_request('/' + name, 'PUT')
        if response.status != 201 or not response.is_json:
            raise CouchDBException(response)

    def get_database(self, name):
        response = self._make_request('/' + name)
        if response.status != 200 or not response.is_json:
            raise CouchDBException(response)
        return response.body

    def delete_database(self, name):
        response = self._make_request('/' + name, 'DELETE')
        if response.status != 200 or not response.is_json:
            raise CouchDBException(response)

    def get_databases(self):
        response = self._make_request('/_all_dbs')
        if response.status != 200 or not response.is_json:
            raise CouchDBException(response)
        return response.body

    def get_active_tasks(self, task_type=None):
        response = self._make_request('/_active_tasks')
        if response.status != 200 or not response.is_json:
            raise CouchDBException(response)

        tasks = response.body
        if task_type:
            tasks = [task for task in tasks if task.type == task_type]

        return tasks

    def _make_request(self, uri, method='GET'):
        headers = {}
        if self._auth:
            headers['Authorization'] = 'Basic ' + self._auth

        self._conn.request(method, uri, None, headers)
        response = self._conn.getresponse()
        body = response.readall()

        if response.status == 401 and callable(self._get_credentials) and not self._auth_active:
            try:
                self._auth_active = True
                creds = self._get_credentials()
                self._auth_active = False

                if creds:
                    auth = creds.username + ':' + creds.password
                    auth = auth.encode()
                    self._auth = b64encode(auth).decode("ascii")
                    return self._make_request(uri, method)
            finally:
                self._auth_active = False

        content_type = response.getheader('content-type')
        if content_type.find('utf-8') >= 0:
            body = body.decode('utf-8')
        else:
            body = body.decode('ascii')

        if content_type.find('text/plain') == 0 and len(body) > 0 and (body[0] == '{' or body[0] == '['):
            content_type = content_type.replace('text/plain', 'application/json')

        if content_type.find('application/json') == 0:
            body = json.loads(body, object_hook=lambda o: namedtuple('Struct', o.keys())(*o.values()))

        return CouchDB.Response(response.status, body, content_type)

