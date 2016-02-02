from gi.repository import Gtk

from src.couchdb import CouchDB
from src.replication import Replication

from ui.view_models.server_history_view_model import ServerHistoryViewModel

class RemoteReplicationDialog:
    def __init__(self, builder):
        self._win = builder.get_object('dialog_remote_replication', target=self, include_children=True)
        self._source_model = Gtk.ListStore(bool, str)
        self.treeview_remote_replication_databases.set_model(self._source_model)
        self._source_model.connect('row-changed', self.on_row_changed)
        self.entry_remote_replication_dialog_server.set_completion(ServerHistoryViewModel.completion())
        self._replications = None
        self._model = None
        self._remote_couchdb = None

    def run(self, model):
        self._model = model
        self._remote_couchdb = None
        self._replications = []
        result = self._win.run()
        self._win.hide()
        return result

    def get_couchdb(self):
        return CouchDB(self.server, self.port, self.is_port_secure, self._model.couchdb.get_credentials_callback)

    def _get_selected_database_rows(self):
        selected_databases = []
        model = self._source_model
        itr = model.get_iter_first()
        while itr is not None:
            if model.get_value(itr, 0):
                db = model.get_value(itr, 1)
                selected_databases.append(db)
            itr = model.iter_next(itr)
        return selected_databases

    def set_button_replicate_active_state(self):
        sensitive = len(self._get_selected_database_rows()) > 0
        self.button_remote_replications_dialog_replicate.set_sensitive(sensitive)

    # region Properties
    @property
    def replications(self):
        return self._replications

    @property
    def server(self):
        return self.entry_remote_replication_dialog_server.get_text()

    @property
    def port(self):
        return self.comboboxtext_remote_replication_dialog_port.get_active_text()

    @property
    def is_port_443(self):
        return self.port == '443'

    @property
    def is_port_secure(self):
        return self.is_port_443 or self.checkbutton_remote_replication_dialog_secure.get_active()

    @property
    def is_remote_valid(self):
        return len(self.entry_remote_replication_dialog_server.get_text()) > 0 and len(self.port) > 0

    @property
    def drop_first(self):
        return self.checkbutton_remote_replication_dialog_drop_first.get_active()

    @property
    def create(self):
        return self.checkbutton_remote_replication_dialog_create.get_active()

    @property
    def continuous(self):
        return self.checkbutton_remote_replication_dialog_continuous.get_active()

    @property
    def repl_type(self):
        if self.radiobutton_remote_replication_dialog_docs_and_designs.get_active():
            return Replication.ReplType.All
        elif self.radiobutton_remote_replication_dialog_only_docs.get_active():
            return Replication.ReplType.Docs
        elif self.radiobutton_remote_replication_dialog_only_designs.get_active():
            return Replication.ReplType.Designs
    # endregion

    # region Event handlers
    def on_dialog_remote_replication_show(self, dialog):
        self._source_model.clear()

    def on_entry_remote_replication_dialog_server_changed(self, entry):
        text = self.entry_remote_replication_dialog_server.get_text()
        self.button_remote_replication_dialog_connect.set_sensitive(len(text) > 0)

    def on_comboboxtext_remote_replication_dialog_port_changed(self, combobox):
        self.checkbutton_remote_replication_dialog_secure.set_sensitive(self.port != '443')

    def on_cellrenderertoggle_source_toggled(self, widget, path):
        model = self._source_model
        itr = model.get_iter(path)
        val = model.get_value(itr, 0)
        model.set(itr, 0, not val)

    def on_row_changed(self, model, path, iter):
        self.set_button_replicate_active_state()

    def on_button_remote_replication_dialog_connect_clicked(self, button):
        self._source_model.clear()
        self._remote_couchdb = self.get_couchdb()
        databases = self._remote_couchdb.get_databases()
        for database in sorted(databases):
            if not database[0] == '_':
                self._source_model.append([False, database])

    def on_button_remote_replication_dialog_replicate(self, button):
        databases = self._get_selected_database_rows()
        if databases:
            remote_url = self._remote_couchdb.get_url()
            for database in databases:
                source = remote_url + database
                target = database
                repl = Replication(self._model, source, target, continuous=self.continuous, create=self.create, drop_first=self.drop_first, repl_type=self.repl_type)
                self._replications.append(repl)
            self._win.response(Gtk.ResponseType.OK)

    def on_button_remote_replication_dialog_cancel(self, button):
        self._win.response(Gtk.ResponseType.CANCEL)
    # endregion
