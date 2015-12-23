import time
import threading
import webbrowser
import re
import collections

from gi.repository import Gtk, Gdk, GObject

from src.couchdb import CouchDB, CouchDBException
from src.model_mapper import ModelMapper
from src.gtk_helper import GtkHelper
from ui.credentials_dialog import CredentialsDialog
from ui.new_database_dialog import NewDatabaseDialog
from ui.delete_databases_dialog import DeleteDatabasesDialog
from ui.new_single_replication_dialog import NewSingleReplicationDialog


class MainWindow:
    SelectedDatabaseRow = collections.namedtuple('SelectedDatabaseRow', 'index db')

    _couchdb = None

    _auto_update = False
    _auto_update_thread = None
    _auto_update_exit = threading.Event()

    _watch_cursor = Gdk.Cursor.new(Gdk.CursorType.WATCH)

    def __init__(self, builder):
        self._win = builder.get_object('applicationwindow', target=self, include_children=True)
        self._database_menu = builder.get_object('menu_databases', target=self, include_children=True)
        self.credentials_dialog = CredentialsDialog(builder)
        self.new_database_dialog = NewDatabaseDialog(builder)
        self.new_single_replication_dialog = NewSingleReplicationDialog(builder)
        self.delete_databases_dialog = DeleteDatabasesDialog(builder)

        self._database_model = Gtk.ListStore(str, int, int, int, str, str, object)
        self.treeview_databases.set_model(self._database_model)

        self._replication_tasks_model = Gtk.ListStore(str, str, str, int, bool, str, str, object)
        self.treeview_tasks.set_model(self._replication_tasks_model)

        def compare_string_cols(name):
            def compare_strings(a, b):
                return -1 if a < b else 1 if a > b else 0

            def callback(m, x, y, _):
                item_x = ModelMapper.get_item_instance_from_model(m, x)
                item_y = ModelMapper.get_item_instance_from_model(m, y)
                return compare_strings(getattr(item_x, name), getattr(item_y, name))
            return callback

        self._database_model.set_sort_func(0, compare_string_cols('db_name'))

        self._replication_tasks_model.set_sort_func(0, compare_string_cols('source'))
        self._replication_tasks_model.set_sort_func(1, compare_string_cols('target'))
        self._replication_tasks_model.set_sort_func(2, compare_string_cols('state'))

        self._auto_update_thread = threading.Thread(target=self.auto_update_handler)
        self._auto_update_thread.daemon = True
        self._auto_update_thread.start()

        self._win.show_all()

    def auto_update_handler(self):
        while not self._auto_update_exit.wait(5):
            if self._couchdb and self._auto_update:
                try:
                    self.update_replication_tasks()
                    self.update_databases()
                except Exception as e:
                    self.report_error(e)

    def couchdb_request(self, func):
        if self._couchdb:
            GtkHelper.invoke(lambda: self._win.get_window().set_cursor(self._watch_cursor), async=False)

            def task():
                nonlocal func

                try:
                    func()
                except Exception as e:
                    self.report_error(e)
                finally:
                    GtkHelper.invoke(lambda: self._win.get_window().set_cursor(None))

            thread = threading.Thread(target=task)
            thread.start()

    def update_databases(self):
        databases = []
        for name in self._couchdb.get_databases():
            db = self._couchdb.get_database(name)
            databases.append(db)

        def func():
            old_databases = {}
            new_databases = []
            model = self._database_model

            itr = model.get_iter_first()
            while itr is not None:
                db = ModelMapper.get_item_instance_from_model(model, itr)
                old_databases[db.db_name] = model.get_path(itr)
                itr = model.iter_next(itr)

            for db in databases:
                row = MainWindow.new_database_row(db)

                i = old_databases.pop(db.db_name, None)
                if i is not None:
                    model[i] = row
                else:
                    new_databases.append(row)

            deleted_database_paths = [path for path in old_databases.values()]
            for path in reversed(deleted_database_paths):
                itr = model.get_iter(path)
                model.remove(itr)

            for db in new_databases:
                model.append(db)

        GtkHelper.invoke(func, async=False)

    def update_replication_tasks(self):
        tasks = self._couchdb.get_active_tasks('replication')

        def func():
            old_tasks = {}
            new_tasks = []
            model = self._replication_tasks_model

            itr = model.get_iter_first()
            while itr is not None:
                task = ModelMapper.get_item_instance_from_model(model, itr)
                old_tasks[task.replication_id] = model.get_path(itr)
                itr = model.iter_next(itr)

            for task in tasks:
                row = MainWindow.new_replication_task_row(task)

                i = old_tasks.pop(task.replication_id, None)
                if i is not None:
                    model[i] = row
                else:
                    new_tasks.append(row)

            deleted_replication_task_paths = [path for path in old_tasks.values()]
            for path in reversed(deleted_replication_task_paths):
                itr = model.get_iter(path)
                model.remove(itr)

            for task in new_tasks:
                model.append(task)

        GtkHelper.invoke(func, async=False)

    @staticmethod
    def new_database_row(db):
        return ModelMapper(db, [
                            'db_name',
                            'doc_count',
                            lambda i: MainWindow.get_update_sequence(i.update_seq),
                            lambda i: i.disk_size / 1024 / 1024,
                            None,
                            None])

    @staticmethod
    def new_replication_task_row(task):
        return ModelMapper(task, [
            'source',
            'target',
            None,
            lambda t: getattr(t, 'progress', None),
            'continuous',
            lambda t: time.strftime('%H:%M:%S', time.gmtime(t.started_on)),
            lambda t: time.strftime('%H:%M:%S', time.gmtime(t.updated_on))])

    # region Event handlers
    def on_button_connect(self, button):
        self._couchdb = None
        self.infobar_warnings.hide()
        self._replication_tasks_model.clear()
        self._database_model.clear()

        try:
            couchdb = self.get_couchdb()
            self._couchdb = couchdb

            def request():
                self.update_databases()
                self.update_replication_tasks()

            self.couchdb_request(request)
        except Exception as e:
            self.report_error(e)

    def on_infobar_warnings_response(self, widget, user_data):
        self.infobar_warnings.hide()

    def on_menu_databases_refresh(self, menu):
        self.update_databases()

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
                self._couchdb.create_database(name)
                db = self._couchdb.get_database(name)
                row = MainWindow.new_database_row(db)
                self._database_model.append(row)
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

    def on_menu_databases_backup(self, menu):
        selected_databases = self.selected_databases
        if len(selected_databases) == 1 and selected_databases[0].db_name.find('backup$') < 0:
            backup_database = True
            source_name = selected_databases[0].db_name
            target_name = 'backup$' + source_name
            try:
                self._couchdb.get_database(target_name)
                response = GtkHelper.run_dialog(self._win, Gtk.MessageType.QUESTION,
                                                Gtk.ButtonsType.YES_NO,
                                                "Target database already exists, continue?")

                backup_database = response is Gtk.ResponseType.YES
                if backup_database:
                    self._couchdb.delete_database(target_name)
            except Exception as e:
                pass

            if backup_database:
                self.couchdb_request(lambda: self._couchdb.create_replication(source_name, target_name, create_target=True))

    def on_menu_databases_restore(self, menu):
        selected_databases = self.selected_databases
        if len(selected_databases) == 1 and selected_databases[0].db_name.find('backup$') == 0:
            restore_database = True
            source_name = selected_databases[0].db_name
            target_name = source_name[7::]
            try:
                self._couchdb.get_database(target_name)
                response = GtkHelper.run_dialog(self._win, Gtk.MessageType.QUESTION,
                                                Gtk.ButtonsType.YES_NO,
                                                "Target database already exists, continue?")

                restore_database = response is Gtk.ResponseType.YES
                if restore_database:
                    self._couchdb.delete_database(target_name)
            except Exception as e:
                pass

            if restore_database:
                self.couchdb_request(lambda: self._couchdb.create_replication(source_name, target_name, create_target=True))

    def on_menuitem_databases_compact(self, menu):
        selected_databases = self.selected_databases
        if len(selected_databases) == 1:
            name = selected_databases[0].db_name
            self.couchdb_request(lambda: self._couchdb.compact_database(name))

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

    def on_menuitem_databases_replication_new(self, menu):
        selected_databases = self.selected_databases
        if len(selected_databases) == 1:
            db = selected_databases[0]
            self.new_single_replication_dialog.run(db.db_name)

    def on_menu_databases_show(self, menu):
        connected = self._couchdb is not None
        selected_databases = self.selected_databases
        single_row = len(selected_databases) == 1
        multiple_rows = len(selected_databases) > 1
        enable_backup = single_row and selected_databases[0].db_name.find('backup$') < 0
        enable_restore = single_row and selected_databases[0].db_name.find('backup$') == 0

        self.menuitem_databases_new.set_sensitive(connected)
        self.menuitem_databases_refresh.set_sensitive(connected)
        self.menuitem_databases_backup.set_sensitive(enable_backup)
        self.menuitem_databases_restore.set_sensitive(enable_restore)
        self.menuitem_databases_browse_futon.set_sensitive(single_row)
        self.menuitem_databases_browse_fauxton.set_sensitive(single_row)
        self.menuitem_databases_browse_alldocs.set_sensitive(single_row)
        self.menuitem_databases_delete.set_sensitive(single_row or multiple_rows)
        self.menuitem_databases_compact.set_sensitive(single_row)
        self.menuitem_databases_replication_new.set_sensitive(single_row)

    def on_menu_databases_realize(self, menu):
        self.on_menu_databases_show(menu)

    def on_auto_update(self, button):
        self._auto_update = self.checkbuttonAutoUpdate.get_active()

    def on_delete(self, widget, data):
        self._auto_update_exit.set()
        self._auto_update_thread.join()
        Gtk.main_quit()
    # endregion

    def get_couchdb(self):
        return CouchDB(self.server, self.port, self.secure, self.get_credentials)

    def get_credentials(self):
        def func():
            result = None
            if self.credentials_dialog.run() == Gtk.ResponseType.OK:
                result = self.credentials_dialog.credentials
            return result

        return GtkHelper.invoke(func, async=False)

    def report_error(self, err):
        def func():
            text = str(err)
            self.infobar_warnings_message.set_text(text)
            self.infobar_warnings.show()
        GtkHelper.invoke(func)

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
        (model, path_list) = self.treeview_databases.get_selection().get_selected_rows()
        if path_list and len(path_list):
            for path in path_list:
                row = model[path]
                db = ModelMapper.get_item_instance(row)
                rows.append(self.SelectedDatabaseRow(path, db))
        return rows

    @property
    def selected_databases(self):
        rows = self.selected_database_rows
        return [db for path, db in rows]

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

