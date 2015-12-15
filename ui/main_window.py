import time
import threading
import webbrowser
import re
import collections

from gi.repository import Gtk, Gdk, GObject

from lib.couchdb import CouchDB, CouchDBException
from lib.model_mapper import ModelMapper
from ui.credentials_dialog import CredentialsDialog
from ui.new_database_dialog import NewDatabaseDialog
from ui.delete_databases_dialog import DeleteDatabasesDialog


class MainWindow:
    SelectedDatabaseRow = collections.namedtuple('SelectedDatabaseRow', 'index db')

    _couchdb = None

    def __init__(self, builder):
        self._database_model = Gtk.ListStore(str, int, int, int, str, str, object)
        self._database_model.set_sort_func(0,
                                           lambda m, x, y, u:
                                           MainWindow.compare_strings(ModelMapper.get_item_instance_from_model(m, x).db_name,
                                                                      ModelMapper.get_item_instance_from_model(m, y).db_name))

        self._win = builder.get_object('applicationwindow', target=self, include_children=True)
        self._database_menu = builder.get_object('menu_databases', target=self, include_children=True)
        self.credentials_dialog = CredentialsDialog(builder)
        self.new_database_dialog = NewDatabaseDialog(builder)
        self.delete_databases_dialog = DeleteDatabasesDialog(builder)
        self._win.show_all()

    def on_delete(self, widget, data):
        Gtk.main_quit()

    @staticmethod
    def ui_task(func):
        def task():
            nonlocal func
            func()
        GObject.idle_add(task)

    def couchdb_request(self, func):
        if self._couchdb:
            cursor = Gdk.Cursor.new(Gdk.CursorType.WATCH)
            self._win.get_window().set_cursor(cursor)

            def task():
                nonlocal func

                try:
                    func()
                except CouchDBException as e:
                    self.ui_task(lambda ex=e: print('Error: %d' % ex.status))
                except Exception as e:
                    self.ui_task(lambda ex=e: print('Error: %s' % str(ex)))
                finally:
                    self.ui_task(lambda: self._win.get_window().set_cursor(None))

            thread = threading.Thread(target=task)
            thread.start()

    def on_button_connect(self, button):
        self._couchdb = self.get_couchdb()

        def request():
            self.update_databases()

            tasks_store = Gtk.ListStore(str, str, str, int, bool, str, str, object)
            for task in self._couchdb.get_active_tasks('replication'):
                mapper = ModelMapper(task, ['source', 'target', None, 'progress', 'continuous',
                                            lambda t: time.strftime('%H:%M:%S', time.gmtime(t.started_on)),
                                            lambda t: time.strftime('%H:%M:%S', time.gmtime(task.updated_on))])
                tasks_store.append(mapper)
            self.ui_task(lambda: self.treeview_tasks.set_model(tasks_store))

        self.couchdb_request(request)

    def update_databases(self, clear=True):
        old_databases = {}
        new_databases = []
        model = self._database_model

        if clear:
            model.clear()
        else:
            itr = model.get_iter_first()
            while itr is not None:
                db = ModelMapper.get_item_instance_from_model(model, itr)
                old_databases[db.db_name] = model.get_path(itr)
                itr = model.iter_next(itr)

        for name in self._couchdb.get_databases():
            info = self._couchdb.get_database(name)
            mapper = ModelMapper(info, ['db_name',
                                        'doc_count',
                                        lambda db: MainWindow.get_update_sequence(db.update_seq),
                                        lambda db: db.disk_size / 1024 / 1024,
                                        None,
                                        None])
            if clear:
                new_databases.append(mapper)
            else:
                i = old_databases.pop(name, None)
                if i is not None:
                    model[i] = mapper
                else:
                    new_databases.append(mapper)

        for db in new_databases:
            model.append(db)

        self.treeview_databases.set_model(model)

    def on_menu_databases_refresh(self, menu):
        self.update_databases(clear=False)

    def on_comboboxtext_port_changed(self, widget):
        self.checkbutton_secure.set_sensitive(self.port != '443')

    def on_database_button_press_event(self, menu, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self._database_menu.popup(None, None, None, None, event.button, event.time)
            return True

    def on_databases_popup_menu(self, widget):
        self._database_menu.popup(None, None, None, None, 0, 0)
        return True

    def on_menu_databases_new(self, widget):
        if self.new_database_dialog.run() == Gtk.ResponseType.OK:
            name = self.new_database_dialog.name

            def request():
                if self._couchdb.create_database(name):
                    self._couchdb.get_database(name)
            self.couchdb_request(request)

    def on_menu_databases_delete(self, menu):
        selected_database_rows = [item for item in self.selected_database_rows if item.db.db_name[0] != '_']
        if len(selected_database_rows) > 0:
            result = self.delete_databases_dialog.run(selected_database_rows)
            if result == Gtk.ResponseType.OK:
                model = self.treeview_databases.get_model()

                def request():
                    for row in reversed(self.delete_databases_dialog.selected_database_rows):
                        self._couchdb.delete_database(row.db.db_name)
                        itr = model.get_iter(row.index)
                        model.remove(itr)
                self.couchdb_request(request)

    def on_menu_databases_browse_futon(self, menu):
        selected_databases = self.selected_database_rows
        if len(selected_databases) > 0:
            db = selected_databases[0].db
            url = 'https' if self.secure else 'http'
            url += '://' + self.server + ':' + self.port + '/_utils/database.html?' + db.db_name
            webbrowser.open_new_tab(url)

    def on_menu_databases_browse_fauxton(self, menu):
        selected_databases = self.selected_database_rows
        if len(selected_databases) > 0:
            db = selected_databases[0].db
            url = 'https' if self.secure else 'http'
            url += '://' + self.server + ':' + self.port + '/_utils/fauxton/index.html#/database/' + db.db_name + '/_all_docs?limit=20'
            webbrowser.open_new_tab(url)

    def on_menu_databases_browse_alldocs(self, menu):
        selected_databases = self.selected_database_rows
        if len(selected_databases) > 0:
            db = selected_databases[0].db
            url = 'https' if self.secure else 'http'
            url += '://' + self.server + ':' + self.port + '/' + db.db_name + '/_all_docs?limit=100'
            webbrowser.open_new_tab(url)

    def on_menu_databases_show(self, menu):
        connected = self._couchdb is not None
        selected_databases = self.selected_database_rows
        single_row = len(selected_databases) == 1
        multiple_rows = len(selected_databases) > 1

        self.menuitem_databases_new.set_sensitive(connected)
        self.menuitem_databases_refresh.set_sensitive(connected)
        self.menuitem_databases_browse_futon.set_sensitive(single_row)
        self.menuitem_databases_browse_fauxton.set_sensitive(single_row)
        self.menuitem_databases_browse_alldocs.set_sensitive(single_row)
        self.menuitem_databases_delete.set_sensitive(single_row or multiple_rows)
        self.menuitem_databases_compact.set_sensitive(single_row or multiple_rows)

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

            if self.credentials_dialog.run() == Gtk.ResponseType.OK:
                result = self.credentials_dialog.credentials
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

    @property
    def selected_database_rows(self):
        rows = []
        (model, pathlist) = self.treeview_databases.get_selection().get_selected_rows()
        if pathlist and len(pathlist):
            for path in pathlist:
                row = model[path]
                db = ModelMapper.get_item_instance(row)
                rows.append(self.SelectedDatabaseRow(path, db))
        return rows

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

    @staticmethod
    def compare_strings(a, b):
        if a < b:
            return -1
        elif a > b:
            return 1
        else:
            return 0
