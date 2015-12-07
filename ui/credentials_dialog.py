from gi.repository import Gtk, Gdk, GObject

class CredentialsDialog:
    _username = None
    _password = None

    def __init__(self, builder):
        self._win = builder.get_object('dialog_credentials', target=self)
        builder.get_children('dialog_credentials', self)

    def run(self):
        result = self._win.run()
        self._win.hide()
        return result

    def on_button_credentials_dialog_ok(self, button):
        self._username = self.entry_username.get_text()
        self._password = self.entry_password.get_text()
        self._win.response(Gtk.ButtonsType.OK)

    def on_button_credentials_dialog_cancel(self, button):
        self._win.response(Gtk.ButtonsType.CANCEL)
        self._win.hide()

    def on_entry_username_changed(self, text):
        text = self.entry_username.get_text()
        self.button_credentials_dialog_ok.set_sensitive(len(text) > 0)

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password
