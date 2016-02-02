from gi.repository import Gtk

from src.keyring import Keyring


def _set_history(store):
    for server in Keyring.get_server_history():
        store.append([server])


class ServerHistoryViewModel:
    _store = Gtk.ListStore(str)
    _set_history(_store)

    @staticmethod
    def completion():
        completion = Gtk.EntryCompletion()
        completion.set_model(ServerHistoryViewModel._store)
        completion.set_text_column(0)
        return completion

    @staticmethod
    def append(server):
        if not ServerHistoryViewModel._contains(server):
            ServerHistoryViewModel._store.append([server])
            ServerHistoryViewModel._save()

    @staticmethod
    def _save():
        servers = ServerHistoryViewModel._entries()
        Keyring.update_server_history(list(servers))

    @staticmethod
    def _contains(server):
        return server in ServerHistoryViewModel._entries()

    @staticmethod
    def _entries():
        servers = set()

        def func(model, path, itr):
            value = model[itr][0]
            if value:
                servers.add(value)
        ServerHistoryViewModel._store.foreach(func)
        return servers
