from gi.repository import Gtk

from src.gtk_helper import GtkHelper
from src.replication import Replication

from ui.view_models.server_history_view_model import ServerHistoryViewModel


class NewSingleReplicationDialog:
    def __init__(self, builder):
        self._win = builder.get_object('dialog_new_replication', target=self, include_children=True)
        self._target_model = Gtk.ListStore(str)
        self._target_model.connect('row-inserted', self.on_target_model_row_added)
        self._target_model.connect('row-deleted', self.on_target_model_row_deleted)
        self.treeview_new_replication_dialog_targets.set_model(self._target_model)
        self.entry_new_replication_dialog_server.set_completion(ServerHistoryViewModel.completion())
        self._replications = None
        self._model = None

    def run(self, model, source_name):
        self._model = model
        self._replications = []
        self.entry_new_replication_dialog_source.set_text(source_name)
        result = self._win.run()
        self._win.hide()
        return result

    def set_add_target_button_state(self):
        target_name = self.entry_new_replication_dialog_target.get_text()
        sensitive = len(target_name) > 0
        if sensitive and self.is_remote_active:
            sensitive = self.is_remote_valid
        self.button_new_replication_dialog_add_target.set_sensitive(sensitive)

    def set_remove_target_button_state(self):
        selected_row_count = len(self.selected_target_rows[1])
        self.button_new_replication_dialog_delete.set_sensitive(selected_row_count > 0)

    def set_replicate_button_state(self):
        count = len(self._target_model)
        self.button_new_replication_dialog_replicate.set_sensitive(count > 0)

    def get_new_target(self):
        target = ''
        if self.is_remote_active:
            target = 'https' if self.is_remote_port_secure else 'http'
            target += '://' + self.entry_new_replication_dialog_server.get_text()
            if (self.is_remote_port_secure and self.remote_port != '443') or (not self.is_remote_port_secure and self.remote_port != '80'):
                target += ':' + self.remote_port + '/'
            else:
                target += '/'

        target += self.entry_new_replication_dialog_target.get_text()
        return target

    # region Properties
    @property
    def remote_port(self):
        return self.comboboxtext_new_replication_dialog_port.get_active_text()

    @property
    def is_remote_port_443(self):
        return self.remote_port == '443'

    @property
    def is_remote_port_secure(self):
        return self.is_remote_port_443 or self.checkbutton_new_replication_dialog_secure.get_active()

    @property
    def is_remote_active(self):
        return self.checkbutton_new_replication_dialog_remote.get_active()

    @property
    def is_remote_valid(self):
        return len(self.entry_new_replication_dialog_server.get_text()) > 0 and len(self.remote_port) > 0

    @property
    def selected_target_rows(self):
        return self.treeview_new_replication_dialog_targets.get_selection().get_selected_rows()

    @property
    def selected_targets(self):
        targets = []
        (model, path_list) = self.selected_target_rows
        if path_list and len(path_list):
            for path in path_list:
                row = model[path]
                targets.append(row[0])
        return targets

    @property
    def replications(self):
        return self._replications

    @property
    def source(self):
        return self.entry_new_replication_dialog_source.get_text()

    @property
    def drop_first(self):
        return self.checkbutton_new_replication_dialog_drop_first.get_active()

    @property
    def create(self):
        return self.checkbutton_new_replication_dialog_create.get_active()

    @property
    def continuous(self):
        return self.checkbutton_new_replication_dialog_continuous.get_active()

    @property
    def repl_type(self):
        if self.radiobutton_new_replication_dialog_docs_and_designs.get_active():
            return Replication.ReplType.All
        elif self.radiobutton_new_replication_dialog_only_docs.get_active():
            return Replication.ReplType.Docs
        elif self.radiobutton_new_replication_dialog_only_designs.get_active():
            return Replication.ReplType.Designs
    # endregion

    # region Event handlers
    def on_dialog_new_replication_show(self, dialog):
        self.entry_new_replication_dialog_target.set_text('')
        self._target_model.clear()
        self.set_remove_target_button_state()

    def on_checkbutton_new_replication_dialog_remote(self, button):
        active = self.is_remote_active
        self.entry_new_replication_dialog_server.set_sensitive(active)
        self.comboboxtext_new_replication_dialog_port.set_sensitive(active)
        self.checkbutton_new_replication_dialog_secure.set_sensitive(active and not self.is_remote_port_443)
        self.set_add_target_button_state()

    def on_comboboxtext_new_replication_dialog_port_changed(self, combobox):
        self.checkbutton_new_replication_dialog_secure.set_sensitive(not self.is_remote_port_443)
        self.set_add_target_button_state()

    def on_entry_new_replication_dialog_server_changed(self, entry):
        self.set_add_target_button_state()

    def on_entry_new_replication_dialog_target_changed(self, entry):
        self.set_add_target_button_state()

    def on_button_new_replication_dialog_add_target(self, button):
        new_target = self.get_new_target()
        self._target_model.append([new_target])

    def on_treeview_new_replication_dialog_targets_row_activated(self, treeview, path, column):
        self.set_remove_target_button_state()

    def on_button_new_replication_dialog_delete_clicked(self, button):
        selected_row_paths = self.selected_target_rows[1]
        for path in reversed(selected_row_paths):
            itr = self._target_model.get_iter(path)
            self._target_model.remove(itr)

    def on_target_model_row_added(self, mode, path, user_data):
        GtkHelper.idle(self.set_replicate_button_state)

    def on_target_model_row_deleted(self, path, user_data):
        def func():
            self.set_remove_target_button_state()
            self.set_replicate_button_state()
        GtkHelper.idle(func)

    def on_treeview_new_replication_dialog_targets_select_all(self, widget):
        GtkHelper.idle(self.set_remove_target_button_state)

    def on_button_new_replication_dialog_replicate(self, button):
        self._replications = []

        for row in self._target_model:
            target = row[0]
            replication = Replication(
                model=self._model,
                source=self.source, target=target, continuous=self.continuous,
                create=self.create, drop_first=self.drop_first, repl_type=self.repl_type)
            self._replications.append(replication)

        self._win.response(Gtk.ResponseType.OK)

    def on_button_new_replication_dialog_cancel(self, button):
        self._win.response(Gtk.ResponseType.CANCEL)
    # endregion
