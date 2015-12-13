from collections import namedtuple
from gi.repository import Gtk


class CredentialsDialog:
    Credentials = namedtuple('Credentials', 'username password')

    _username = None
    _password = None

    def __init__(self, builder):
        self._win = builder.get_object('dialog_credentials', target=self, include_children=True)

    def run(self):
        result = self._win.run()
        self._win.hide()
        return result

    def on_button_credentials_dialog_ok(self, button):
        self._username = self.entry_username.get_text()
        self._password = self.entry_password.get_text()
        self._win.response(Gtk.ResponseType.OK)

    def on_button_credentials_dialog_cancel(self, button):
        self._win.response(Gtk.ResponseType.CANCEL)

    def on_entry_username_changed(self, text):
        text = self.entry_username.get_text()
        self.button_credentials_dialog_ok.set_sensitive(len(text) > 0)

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password

    @property
    def credentials(self):
        return self.Credentials(self.username, self.password)
