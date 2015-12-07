#!/usr/bin/env python3

import os
import sys
import time
import threading
import webbrowser
import re

from gi.repository import Gtk, Gdk, GObject

from lib.builder import Builder
from lib.couchdb import CouchDB
from lib.model_mapper import ModelMapper
from ui.credentials_dialog import CredentialsDialog


class MainWindow:
    _couchdb = None

    def __init__(self, builder):
        self._win = builder.get_object('applicationwindow', target=self)
        builder.get_children('applicationwindow', self)
        self._database_menu = builder.get_object('menu_databases', target=self)
        builder.get_children('menu_databases', self)
        self.credentials_dialog = CredentialsDialog(builder)
        self._win.show_all()

    def on_delete(self, widget, data):
        Gtk.main_quit()

    def on_button_connect(self, button):
        self._couchdb = self.get_couchdb()
        if self._couchdb:
            cursor = Gdk.Cursor.new(Gdk.CursorType.WATCH)
            self._win.get_window().set_cursor(cursor)

            def connect():
                try:
                    db_store = Gtk.ListStore(str, int, int, int, str, str, object)
                    for db in self._couchdb.get_databases():
                        info = self._couchdb.get_database(db)
                        mapper = ModelMapper(info, ['db_name',
                                                    'doc_count',
                                                    lambda i: MainWindow.get_update_sequence(i.update_seq),
                                                    lambda i: i.disk_size / 1024 / 1024,
                                                    None,
                                                    None])
                        db_store.append(mapper)
                    self.treeview_databases.set_model(db_store)

                    tasks_store = Gtk.ListStore(str, str, str, int, bool, str, str, object)
                    for task in self._couchdb.get_active_tasks('replication'):
                        mapper = ModelMapper(task, ['source', 'target', None, 'progress', 'continuous',
                                                    lambda t: time.strftime('%H:%M:%S', time.gmtime(t.started_on)),
                                                    lambda t: time.strftime('%H:%M:%S', time.gmtime(task.updated_on))])
                        tasks_store.append(mapper)
                        self.treeview_tasks.set_model(tasks_store)
                finally:
                    def done():
                        self._win.get_window().set_cursor(None)
                    GObject.idle_add(done)

            thread = threading.Thread(target=connect)
            thread.start()

    def on_comboboxtext_port_changed(self, widget):
        self.checkbutton_secure.set_sensitive(self.port != '443')

    def on_database_button_press_event(self, menu, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self._database_menu.popup(None, None, None, None, event.button, event.time)
            return True

    def on_databases_popup_menu(self, widget):
        self._database_menu.popup(None, None, None, None, 0, 0)
        return True

    def on_menu_databases_delete(self, menu):
        (model, pathlist) = self.treeview_databases.get_selection().get_selected_rows()
        deleted_paths = []
        for path in pathlist:
            row = model[path]
            db = ModelMapper.get_item_instance(row)
            if db.db_name[0] != '_':
                dialog = Gtk.MessageDialog(self._win, 0, Gtk.MessageType.QUESTION, Gtk.ButtonsType.YES_NO,
                                           "Delete database?")
                dialog.format_secondary_text(db.db_name)
                response = dialog.run()
                dialog.destroy()
                if response == Gtk.ResponseType.YES:
                    self._couchdb.delete_database(db.db_name)
                    deleted_paths.append(path)

        for path in reversed(deleted_paths):
            iter = model.get_iter(path)
            model.remove(iter)

    def on_menu_databases_browse(self, menu):
        (model, pathlist) = self.treeview_databases.get_selection().get_selected_rows()
        if pathlist and len(pathlist):
            path = pathlist[0]
            row = model[path]
            db = ModelMapper.get_item_instance(row)
            url = 'https' if self.secure else 'http'
            url += '://' + self.server + ':' + self.port + '/_utils/database.html?' + db.db_name
            webbrowser.open_new_tab(url)

    def on_menu_databases_show(self, menu):
        (model, pathlist) = self.treeview_databases.get_selection().get_selected_rows()
        single_row = pathlist and len(pathlist) == 1
        multiple_rows = pathlist and len(pathlist) > 1

        self.menuitem_databases_browse.set_sensitive(single_row)
        self.menuitem_databases_delete.set_sensitive(single_row or multiple_rows)

    def on_menu_databases_realize(self, menu):
        self.on_menu_databases_show(menu)

    def show_databases_popup(self, menu, event):
        self._database_menu.popup(None, None, None, None, event.button, event.time)

    def get_couchdb(self):
        return CouchDB(self.server, self.port, self.secure, self.get_credentials)

    def get_credentials(self):
        result = None
        finished = False

        def invoke():
            nonlocal result, finished

            if self.credentials_dialog.run() == Gtk.ButtonsType.OK:
                username = self.credentials_dialog.username
                password = self.credentials_dialog.password
                result = username, password
            else:
                result = None

            finished = True

        GObject.idle_add(invoke)

        while not finished:
            time.sleep(0.5)

        return result

    @property
    def server(self):
        return self.entry_server.get_text()

    @property
    def port(self):
        return self.comboboxtext_port.get_active_text()

    @property
    def secure(self):
        secure = self.checkbutton_secure.get_active()
        return secure or self.port == '443'

    @staticmethod
    def get_update_sequence(val):
        seq = 0

        if isinstance(val, str):
            m = re.search('^\s*(\d+)', val)
            if m:
                groups = m.groups()
                if len(groups) == 1:
                    seq = int(groups[0])
        elif isinstance(val, int):
            seq = val

        return seq

def main():
    ui_path = os.path.dirname(os.path.realpath(sys.argv[0]))
    ui_path = os.path.join(ui_path, 'ui/replication_monitor.glade')
    builder = Builder(ui_path)
    win = MainWindow(builder)
    Gtk.main()

if __name__ == '__main__':
    main()
