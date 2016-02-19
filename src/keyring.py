import keyring
import json
from collections import namedtuple


class Keyring:
    Credentials = namedtuple('Credentials', 'username password')

    _service = 'replication-monitor'
    _server_history = '-server-history'

    def __init__(self):
        raise NotImplementedError

    @staticmethod
    def get_auth(url):
        json_auth = keyring.get_password(Keyring._service, url)
        if json_auth:
            auth = json.loads(json_auth)
            username = auth['username']
            password = auth['password']
            return Keyring.Credentials(username, password)
        else:
            return None

    @staticmethod
    def set_auth(url, username, password):
        json_auth = json.dumps({'username': username, 'password': password})
        keyring.set_password(Keyring._service, url, json_auth)

    @staticmethod
    def remove_auth(url):
        keyring.delete_password(Keyring._service, url)

    @staticmethod
    def update_server_history(servers):
        keyring.set_password(Keyring._service, Keyring._server_history, json.dumps(servers))

    @staticmethod
    def get_server_history():
        json_history = keyring.get_password(Keyring._service, Keyring._server_history)
        history = json.loads(json_history) if json_history else []
        return history
