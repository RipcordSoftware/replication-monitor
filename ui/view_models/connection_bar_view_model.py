from src.gtk_helper import GtkHelper

from ui.view_models.server_history_view_model import ServerHistoryViewModel


class ConnectionBarViewModel:
    def __init__(self, entry_server, comboboxtext_port, checkbutton_secure):
        self._entry_server = entry_server
        self._entry_server.set_completion(ServerHistoryViewModel.completion())
        self._comboboxtext_port = comboboxtext_port
        self._checkbutton_secure = checkbutton_secure

    @property
    @GtkHelper.invoke_func_sync
    def server(self):
        return self._entry_server.get_text()

    @property
    @GtkHelper.invoke_func_sync
    def port(self):
        return self._comboboxtext_port.get_active_text()

    @property
    @GtkHelper.invoke_func_sync
    def secure(self):
        secure = self._checkbutton_secure.get_active()
        return secure or self.port == '443'

    @GtkHelper.invoke_func
    def on_comboboxtext_port_changed(self):
        self._checkbutton_secure.set_sensitive(self.port != '443')

    @staticmethod
    def append_server_to_history(server):
        ServerHistoryViewModel.append(server)
