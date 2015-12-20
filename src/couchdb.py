import json
import threading
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
    def reason(self):
        return self._response.reason

    @property
    def body(self):
        return self._response.body

    @property
    def content_type(self):
        return self._response.content_type

    @property
    def is_json(self):
        return self._response.is_json

    def __str__(self):
        if self.is_json:
            return '{self.status}: {self.reason} - {self.body.reason}'.format(self=self)
        else:
            return '{self.status}: {self.reason}'.format(self=self)


class CouchDB:
    class Response:
        def __init__(self, response, body=None, content_type=None):
            self._response = response
            self._content_type = content_type if content_type is not None else response.getheader('content-type')
            self._body = body

        @property
        def status(self):
            return self._response.status

        @property
        def reason(self):
            return self._response.reason

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
        self._get_credentials = get_credentials
        self.new_connection = lambda: HTTPSConnection(host, port) if secure else HTTPConnection(host, port)
        self._conn = self.new_connection()

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

    def create_replication(self, source, target, create_target=False, continuous=False):
        repl = {'source': source, 'target': target, 'create_target': create_target, 'continuous': continuous}
        json_repl = json.dumps(repl)
        def request():
            conn = self.new_connection()
            self._make_request('/_replicate', 'POST', json_repl, 'application/json', conn)
            conn.close()
        thread = threading.Thread(target=request)
        thread.daemon = True
        thread.start()

    def _make_request(self, uri, method='GET', body=None, content_type=None, conn=None):
        if conn is None:
            conn = self._conn

        headers = {}
        if self._auth:
            headers['Authorization'] = 'Basic ' + self._auth

        if (method == 'PUT' or method == 'POST') and body is not None and content_type is not None:
            headers['Content-Type'] = content_type

        conn.request(method, uri, body, headers)

        response = conn.getresponse()
        response_body = response.readall()

        if response.status == 401 and callable(self._get_credentials) and not self._auth_active:
            try:
                self._auth_active = True
                creds = self._get_credentials()
                self._auth_active = False

                if creds:
                    auth = creds.username + ':' + creds.password
                    auth = auth.encode()
                    self._auth = b64encode(auth).decode("ascii")
                    return self._make_request(uri, method, body, content_type, conn)
            finally:
                self._auth_active = False

        response_content_type = response.getheader('content-type')
        if response_content_type.find('utf-8') >= 0:
            response_body = response_body.decode('utf-8')
        else:
            response_body = response_body.decode('ascii')

        if response_content_type.find('text/plain') == 0 and len(response_body) > 0 and (response_body[0] == '{' or response_body[0] == '['):
            response_content_type = response_content_type.replace('text/plain', 'application/json')

        if response_content_type.find('application/json') == 0:
            response_body = json.loads(response_body, object_hook=lambda o: namedtuple('Struct', o.keys())(*o.values()))

        return CouchDB.Response(response, response_body, response_content_type)

