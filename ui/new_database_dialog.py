import re

from gi.repository import Gtk, Gdk, GObject


class NewDatabaseDialog:
    _name = None

    def __init__(self, builder):
        self._win = builder.get_object('dialog_new_database', target=self)
        builder.get_children('dialog_new_database', self)

    def on_dialog_new_database_show(self, dialog):
        self.entry_new_database_name.set_text('')

    def run(self):
        result = self._win.run()
        self._win.hide()
        return result

    def on_button_new_database_dialog_ok(self, button):
        self._name = self.entry_new_database_name.get_text()
        self._win.response(Gtk.ButtonsType.OK)

    def on_button_new_database_dialog_cancel(self, button):
        self._win.response(Gtk.ButtonsType.CANCEL)
        self._win.hide()

    def on_entry_new_database_name_changed(self, text):
        name = self.entry_new_database_name.get_text()
        m = re.match('^[a-z][a-z0-9_$()+-]*?$', name)
        sensitive = m is not None
        self.button_new_database_dialog_ok.set_sensitive(sensitive)

    @property
    def name(self):
        return self._name
