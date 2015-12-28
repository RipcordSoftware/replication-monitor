from gi.repository import Gtk, Gdk, GObject

from src.gtk_helper import GtkHelper

class NewReplicationsWindow:
    def __init__(self, builder, hide_callback=None):
        self._win = builder.get_object('window_new_replications', target=self, include_children=True)
        self._hide_callback = hide_callback

    def show(self):
        self._win.show()

    def hide(self):
        self._win.hide()

    # region Events
    def on_window_new_replications_show(self, widget):
        pass

    def on_window_new_replications_delete_event(self, widget, user_data):
        if self._hide_callback and callable(self._hide_callback):
            self._hide_callback()
        else:
            self._win.hide()
        return True
    # endregion
