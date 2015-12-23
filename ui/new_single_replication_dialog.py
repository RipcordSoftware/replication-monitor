import re

from gi.repository import Gtk


class NewSingleReplicationDialog:

    def __init__(self, builder):
        self._win = builder.get_object('dialog_new_replication', target=self, include_children=True)
        self._target_model = Gtk.ListStore(str)
        self.treeview_new_replication_dialog_targets.set_model(self._target_model)

    def run(self, source_name):
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

    def get_new_target(self):
        target = ''
        if self.is_remote_active:
            target = 'https' if self.is_remote_port_secure else 'http'
            target += '://' + self.entry_new_replication_dialog_server.get_text() + ':' + self.remote_port + '/'

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
    # endregion

    # region Event handlers
    def on_dialog_new_replication_show(self, dialog):
        self.entry_new_replication_dialog_target.set_text('')
        self._target_model.clear()
        pass

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
        self.button_new_replication_dialog_add_delete.set_sensitive(len(self.selected_targets) > 0)

    def on_button_new_replication_dialog_add_delete_clicked(self, button):
        print('on_button_new_replication_dialog_add_delete_clicked')

    def on_button_new_replication_dialog_replicate(self, button):
        pass

    def on_button_new_replication_dialog_cancel(self, button):
        self._win.response(Gtk.ResponseType.CANCEL)
    # endregion
