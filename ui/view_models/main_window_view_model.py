from gi.repository import Gtk, Gdk

from src.gtk_helper import GtkHelper


class MainWindowViewModel:
    _watch_cursor = Gdk.Cursor.new(Gdk.CursorType.WATCH)

    def __init__(self, main_window, new_replications_window):
        self._main_window = main_window
        self._new_replications_window = new_replications_window

    @GtkHelper.invoke_func
    def reset_window_titles(self):
        title = self._get_default_window_title(self._main_window)
        self._main_window.set_title(title)
        title = self._get_default_window_title(self._new_replications_window)
        self._new_replications_window.set_title(title)

    @GtkHelper.invoke_func
    def update_window_titles(self, model):
        title = self._get_default_window_title(self._main_window)
        title += ' - ' + model.url
        self._main_window.set_title(title)
        title = self._get_default_window_title(self._new_replications_window)
        title += ' - ' + model.url
        self._new_replications_window.set_title(title)

    @GtkHelper.invoke_func_sync
    def set_watch_cursor(self):
        self._main_window.get_window().set_cursor(self._watch_cursor)

    @GtkHelper.invoke_func_sync
    def set_default_cursor(self):
        self._main_window.get_window().set_cursor(None)

    # region Static methods
    @staticmethod
    def _get_default_window_title(window):
        title = window.get_title().split('-')[0].rstrip(' ')
        return title
    # endregion
