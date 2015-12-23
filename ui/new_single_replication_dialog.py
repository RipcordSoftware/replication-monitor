import re

from gi.repository import Gtk


class NewSingleReplicationDialog:

    def __init__(self, builder):
        self._win = builder.get_object('dialog_new_replication', target=self, include_children=True)

    def on_dialog_new_replication_show(self, dialog):
        pass

    def run(self):
        result = self._win.run()
        self._win.hide()
        return result

    def on_button_new_replication_dialog_replicate(self, button):
        pass

    def on_button_new_replication_dialog_cancel(self, button):
        self._win.response(Gtk.ResponseType.CANCEL)

