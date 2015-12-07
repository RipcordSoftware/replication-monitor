import json
from collections import namedtuple
from http.client import HTTPConnection, HTTPSConnection
from base64 import b64encode


class CouchDB:
    def __init__(self, host, port, secure, username=None, password=None):
        self._conn = HTTPSConnection(host, port) if secure else HTTPConnection(host, port)

        self._auth = None
        if username and password is not None:
            creds = '' + username + ':' + password
            creds = creds.encode()
            self._auth = b64encode(creds).decode("ascii")

    def get_database(self, name):
        database = self._make_request('/' + name)
        return database[1]

    def delete_database(self, name):
        response = self._make_request('/' + name, 'DELETE')
        return response[0] == 200

    def get_databases(self):
        databases = self._make_request('/_all_dbs')
        return databases[1]

    def get_active_tasks(self, task_type=None):
        tasks = self._make_request('/_active_tasks')

        if task_type:
            tasks = [task for task in tasks[1] if task.type == task_type]

        return tasks

    def _make_request(self, uri, method='GET'):
        headers = {}
        if self._auth:
            headers['Authorization'] = 'Basic ' + self._auth

        self._conn.request(method, uri, None, headers)
        response = self._conn.getresponse()
        body = response.readall()
        if response.status >= 200 and response.status < 300:
            content_type = response.getheader('content-type')
            if content_type.find('utf-8') >= 0:
                body = body.decode('utf-8')
            if content_type.find('application/json') == 0 or (content_type.find('text/plain') == 0 and (body[0] == '{' or body[0] == '[')):
                body = json.loads(body, object_hook=lambda o: namedtuple('Struct', o.keys())(*o.values()))
            return response.status, body
        else:
            return response.status, None
