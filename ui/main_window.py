import time
import threading
import webbrowser
import re
import collections
from urllib.parse import urlparse
from collections import namedtuple
import concurrent.futures

from gi.repository import Gtk, Gdk

from src.couchdb import CouchDB
from src.model_mapper import ModelMapper
from src.gtk_helper import GtkHelper
from src.keyring import Keyring
from src.replication import Replication
from src.new_replication_queue import NewReplicationQueue
from ui.credentials_dialog import CredentialsDialog
from ui.new_database_dialog import NewDatabaseDialog
from ui.delete_databases_dialog import DeleteDatabasesDialog
from ui.new_single_replication_dialog import NewSingleReplicationDialog
from ui.new_multiple_replications_dialog import NewMultipleReplicationDialog
from ui.remote_replication_dialog import RemoteReplicationDialog
from ui.new_replications_window import NewReplicationsWindow
from ui.about_dialog import AboutDialog


class MainWindow:
    SelectedDatabaseRow = collections.namedtuple('SelectedDatabaseRow', 'index db')

    _couchdb = None

    _auto_update = False
    _auto_update_thread = None
    _auto_update_exit = threading.Event()

    _watch_cursor = Gdk.Cursor.new(Gdk.CursorType.WATCH)

    DRAG_BUTTON_MASK = Gdk.ModifierType.BUTTON1_MASK
    DRAG_TARGETS = [('text/plain', 0, 0)]
    DRAG_ACTION = Gdk.DragAction.COPY

    def __init__(self, builder):
        self._win = builder.get_object('applicationwindow', target=self, include_children=True)
        self._database_menu = builder.get_object('menu_databases', target=self, include_children=True)
        self.credentials_dialog = CredentialsDialog(builder)
        self.new_database_dialog = NewDatabaseDialog(builder)
        self.new_single_replication_dialog = NewSingleReplicationDialog(builder)
        self.new_multiple_replication_dialog = NewMultipleReplicationDialog(builder)
        self.delete_databases_dialog = DeleteDatabasesDialog(builder)
        self._new_replications_window = NewReplicationsWindow(builder, self.on_hide_new_replication_window)
        self.remote_replication_dialog = RemoteReplicationDialog(builder)
        self.about_dialog = AboutDialog(builder)

        self._database_model = Gtk.ListStore(str, int, int, int, str, int, object)
        self.treeview_databases.set_model(self._database_model)
        self.treeview_databases.enable_model_drag_source(self.DRAG_BUTTON_MASK, self.DRAG_TARGETS, self.DRAG_ACTION)
        self.treeview_databases.enable_model_drag_dest(self.DRAG_TARGETS, self.DRAG_ACTION)

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

        self._replication_queue = NewReplicationQueue(self.report_error)

        self._auto_update_thread = threading.Thread(target=self.auto_update_handler)
        self._auto_update_thread.daemon = True
        self._auto_update_thread.start()

        self.reset_statusbar()

        self._win.show_all()

    def auto_update_handler(self):
        while not self._auto_update_exit.wait(5):
            if self._couchdb and self._auto_update:
                try:
                    GtkHelper.idle(lambda: self.spinner_auto_update.set_visible(True))
                    with self._couchdb.clone() as couchdb:
                        self.update_replication_tasks(couchdb)
                        self.update_databases(couchdb)
                except Exception as e:
                    self.report_error(e)
                finally:
                    GtkHelper.idle(lambda: self.spinner_auto_update.set_visible(False))

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

    def reset_statusbar(self):
        self.statusbar.remove_all(0)
        self.statusbar.push(0, 'Not Connected')

    def update_statusbar(self):
        def func():
            try:
                with self._couchdb.clone() as couchdb:
                    signature = couchdb.get_signature()
                    server = couchdb.db_type.name + ' ' + str(signature.version)

                    auth_details = 'Admin Party'
                    session = couchdb.get_session()
                    user_ctx = session.userCtx
                    if user_ctx and user_ctx.name:
                        auth_details = user_ctx.name
                        roles = ''
                        for role in user_ctx.roles:
                            roles += ', ' + role if len(roles) > 0 else role
                        auth_details += ' [' + roles + ']'

                    status = server + ' - ' + auth_details
                    self.statusbar.push(0, status)
            except Exception as e:
                GtkHelper.invoke(self.reset_statusbar)
        thread = threading.Thread(target=func)
        thread.run()

    def update_databases(self, couchdb=None):
        couchdb = couchdb if couchdb else self._couchdb

        databases = []

        def get_database_worker(couchdb, name):
            with couchdb:
                db = couchdb.get_database(name)
                limit = couchdb.get_revs_limit(name)
                db = self.append_field(db, ('revs_limit', limit), 'Database')
                databases.append(db)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for name in couchdb.get_databases():
                futures.append(executor.submit(get_database_worker, couchdb.clone(), name))
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except:
                    raise

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

    def update_replication_tasks(self, couchdb=None):
        couchdb = couchdb if couchdb else self._couchdb

        tasks = couchdb.get_active_tasks('replication')

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
            for path in sorted(deleted_replication_task_paths, reverse=True):
                itr = model.get_iter(path)
                model.remove(itr)

            for task in new_tasks:
                model.append(task)

        GtkHelper.invoke(func, async=False)

    def get_couchdb(self):
        return CouchDB(self.server, self.port, self.secure, self.get_credentials)

    def get_credentials(self, server_url):
        def func():
            credentials = Keyring.get_auth(server_url)
            username = credentials.username if credentials else None
            password = credentials.password if credentials else None

            result = None
            if self.credentials_dialog.run(server_url, username, password) == Gtk.ResponseType.OK:
                result = self.credentials_dialog.credentials
                if self.credentials_dialog.save_credentials:
                    Keyring.set_auth(server_url, result.username, result.password)

            GtkHelper.idle(self.update_statusbar)

            return result

        return GtkHelper.invoke(func, async=False)

    def close(self):
        self._auto_update_exit.set()
        self._auto_update_thread.join()
        Gtk.main_quit()

    def report_error(self, err):
        def func():
            text = str(err)
            self.infobar_warnings_message.set_text(text)
            self.infobar_warnings.show()
        GtkHelper.invoke(func)

    def queue_replication(self, repl):
        ref = self._new_replications_window.add(repl)
        self._replication_queue.put(repl,
                                    lambda: self._new_replications_window.update_success(ref),
                                    lambda err: self._new_replications_window.update_failed(ref, err))

    # region Properties
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
    # endregion

    # region Event handlers
    def on_button_connect(self, button):
        self._couchdb = None
        self.infobar_warnings.hide()
        self._replication_tasks_model.clear()
        self._database_model.clear()
        self.reset_statusbar()

        try:
            couchdb = self.get_couchdb()
            self._couchdb = couchdb

            def request():
                self.update_databases()
                self.update_replication_tasks()
                self.update_statusbar()

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
            except:
                pass

            if backup_database:
                repl = Replication(self._couchdb.clone(), source_name, target_name, drop_first=True, create=True)
                self.queue_replication(repl)

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
            except:
                pass

            if restore_database:
                repl = Replication(self._couchdb.clone(), source_name, target_name, drop_first=True, create=True)
                self.queue_replication(repl)

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
        replications = None
        selected_databases = self.selected_databases
        selected_count = len(selected_databases)

        if selected_count == 1:
            db = selected_databases[0]
            result = self.new_single_replication_dialog.run(self._couchdb, db.db_name)
            if result == Gtk.ResponseType.OK:
                replications = self.new_single_replication_dialog.replications
        elif selected_count > 1:
            source_names = [db.db_name for db in selected_databases]
            result = self.new_multiple_replication_dialog.run(self._couchdb, source_names)
            if result == Gtk.ResponseType.OK:
                replications = self.new_multiple_replication_dialog.replications

        if replications:
            self.checkmenuitem_view_new_replication_window.set_active(True)
            for repl in replications:
                self.queue_replication(repl)

    def on_menuitem_databases_replication_remote(self, menu):
        replications = None
        result = self.remote_replication_dialog.run(self._couchdb)
        if result == Gtk.ResponseType.OK:
            replications = self.remote_replication_dialog.replications

        if replications:
            self.checkmenuitem_view_new_replication_window.set_active(True)
            for repl in replications:
                self.queue_replication(repl)

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
        self.menuitem_databases_replication_new.set_sensitive(single_row or multiple_rows)
        self.menuitem_databases_replication_from_remote.set_sensitive(connected)

    def on_menu_databases_realize(self, menu):
        self.on_menu_databases_show(menu)

    def on_auto_update(self, button):
        self._auto_update = self.checkbuttonAutoUpdate.get_active()

    def on_delete(self, widget, data):
        self.close()

    def on_checkmenuitem_view_new_replication_window_toggled(self, menu):
        active = self.checkmenuitem_view_new_replication_window.get_active()
        if active:
            self._new_replications_window.show()
        else:
            self._new_replications_window.hide()

    def on_hide_new_replication_window(self):
        self.checkmenuitem_view_new_replication_window.set_active(False)

    def on_imagemenuitem_file_quit(self, menu):
        self.close()

    def on_treeview_databases_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        if self._couchdb and info == 0:
            text = data.get_text()
            urls = text.split('\n')
            for url in urls:
                if url.find('http') == 0:
                    u = urlparse(url)
                    if not (u.hostname == self.server and u.port == self.port):
                        target = u.path[1::]
                        repl = Replication(self._couchdb, url, target, continuous=False, create=True)
                        self.queue_replication(repl)
            self.checkmenuitem_view_new_replication_window.set_active(True)

    def on_treeview_databases_drag_data_get(self, widget, drag_context, data, info, time):
        selected_databases = self.selected_databases
        selected_count = len(selected_databases)
        if selected_count > 0:
            text = ''
            url = self._couchdb.get_url()
            for db in selected_databases:
                if len(text) > 0:
                    text += '\n'
                text += url + db.db_name
            data.set_text(text, -1)

    def on_menuitem_help_about_activate(self, menu):
        self.about_dialog.run()
    # endregion

    # region Static methods
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
    def new_database_row(db):
        return ModelMapper(db, [
            'db_name',
            'doc_count',
            lambda i: MainWindow.get_update_sequence(i.update_seq),
            lambda i: i.disk_size / 1024 / 1024,
            lambda i: 'Yes' if i.compact_running else 'No',
            'revs_limit'])

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

    @staticmethod
    def append_field(source, field, name='NewType'):
        fields = [key for key in source._fields]
        fields.append(field[0])
        NewType = namedtuple(name, fields)
        values = [value for value in iter(source)]
        values.append(field[1])
        return NewType(*values)

# endregion

