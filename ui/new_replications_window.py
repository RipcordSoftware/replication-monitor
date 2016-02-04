from gi.repository import Gtk, Gdk, GObject

from src.gtk_helper import GtkHelper


class NewReplicationsWindow:
    def __init__(self, builder, hide_callback=None):
        self._win = builder.get_object('window_new_replications', target=self, include_children=True)
        self._hide_callback = hide_callback
        self._model = Gtk.ListStore(str, str, str, str)
        self.treeview_new_replications_queue.set_model(self._model)

    def get_title(self):
        return self._win.get_title()

    def set_title(self, title):
        return self._win.set_title(title)

    def show(self):
        self._win.show()

    def hide(self):
        self._win.hide()

    def add(self, repl):
        itr = self._model.append([repl.source, repl.target, 'image-loading', ''])
        path = self._model.get_path(itr)
        return Gtk.TreeRowReference.new(self._model, path)

    def update_success(self, reference):
        assert isinstance(reference, Gtk.TreeRowReference)
        if reference.valid():
            def func():
                path = reference.get_path()
                self._model[path][2] = 'emblem-default'
            GtkHelper.invoke(func)

    def update_failed(self, reference, err=None):
        assert isinstance(reference, Gtk.TreeRowReference)
        if reference.valid():
            def func():
                path = reference.get_path()
                self._model[path][2] = 'emblem-important'
                if err:
                    if isinstance(err, Exception):
                        self._model[path][3] = '{}: {}'.format(type(err).__name__, str(err))
                    else:
                        self._model[path][3] = str(err)
            GtkHelper.invoke(func)

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
