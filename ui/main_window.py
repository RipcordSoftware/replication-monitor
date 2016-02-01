import threading
import webbrowser
import re
from urllib.parse import urlparse

from gi.repository import Gtk, Gdk

from src.gtk_helper import GtkHelper
from src.keyring import Keyring
from src.replication import Replication

from src.new_replication_queue import NewReplicationQueue
from ui.dialogs.credentials_dialog import CredentialsDialog
from ui.dialogs.new_database_dialog import NewDatabaseDialog
from ui.dialogs.delete_databases_dialog import DeleteDatabasesDialog
from ui.dialogs.new_single_replication_dialog import NewSingleReplicationDialog
from ui.dialogs.new_multiple_replications_dialog import NewMultipleReplicationDialog
from ui.dialogs.remote_replication_dialog import RemoteReplicationDialog
from ui.dialogs.about_dialog import AboutDialog

from ui.new_replications_window import NewReplicationsWindow

from ui.main_window_model import MainWindowModel

from ui.view_models.main_window_view_model import MainWindowViewModel
from ui.view_models.databases_view_model import DatabasesViewModel
from ui.view_models.replication_tasks_view_model import ReplicationTasksViewModel
from ui.view_models.statusbar_view_model import StatusBarViewModel
from ui.view_models.infobar_warnings_view_model import InfobarWarningsViewModel
from ui.view_models.connection_bar_view_model import ConnectionBarViewModel


class MainWindow:
    _auto_update = False
    _auto_update_thread = None
    _auto_update_exit = threading.Event()

    _watch_cursor = Gdk.Cursor.new(Gdk.CursorType.WATCH)

    def __init__(self, builder):
        self._model = None

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

        self._main_window_view_model = MainWindowViewModel(self._win, self._new_replications_window)

        self._databases = DatabasesViewModel(self.treeview_databases)
        del self.treeview_databases

        self._replication_tasks = ReplicationTasksViewModel(self.treeview_tasks)
        del self.treeview_tasks

        self._replication_queue = NewReplicationQueue(self.report_error)

        self._auto_update_thread = threading.Thread(target=self.auto_update_handler)
        self._auto_update_thread.daemon = True
        self._auto_update_thread.start()

        self._connection_bar = ConnectionBarViewModel(self.entry_server, self.comboboxtext_port, self.checkbutton_secure)
        del self.entry_server
        del self.comboboxtext_port
        del self.checkbutton_secure

        self._statusbar = StatusBarViewModel(self.statusbar, self.spinner_auto_update)
        del self.statusbar
        del self.spinner_auto_update
        self._statusbar.reset()

        self._infobar_warnings = InfobarWarningsViewModel(self.infobar_warnings, self.infobar_warnings_message)
        del self.infobar_warnings
        del self.infobar_warnings_message

        self._win.show_all()

    def auto_update_handler(self):
        while not self._auto_update_exit.wait(5):
            if self._model and self._auto_update:
                try:
                    self._statusbar.show_busy_spinner(True)
                    self._replication_tasks.update(self._model.replication_tasks)
                    self._databases.update(self._model.databases)
                except Exception as e:
                    self.report_error(e)
                finally:
                    self._statusbar.show_busy_spinner(False)

    # TODO: rename as model_request
    def couchdb_request(self, func):
        if self._model:
            self._main_window_view_model.set_watch_cursor()

            def task():
                nonlocal func

                try:
                    func()
                except Exception as e:
                    self.report_error(e)
                finally:
                    self._main_window_view_model.set_default_cursor()

            thread = threading.Thread(target=task)
            thread.start()

    @GtkHelper.invoke_func_sync
    def get_credentials(self, server_url):
        credentials = Keyring.get_auth(server_url)
        username = credentials.username if credentials else None
        password = credentials.password if credentials else None

        result = None
        if self.credentials_dialog.run(server_url, username, password) == Gtk.ResponseType.OK:
            result = self.credentials_dialog.credentials
            if self.credentials_dialog.save_credentials:
                Keyring.set_auth(server_url, result.username, result.password)
        self._statusbar.update(self._model)
        return result

    def close(self):
        self._auto_update_exit.set()
        self._auto_update_thread.join()
        Gtk.main_quit()

    @GtkHelper.invoke_func
    def report_error(self, err):
        self._infobar_warnings.message = str(err)

    def queue_replication(self, repl):
        ref = self._new_replications_window.add(repl)
        self._replication_queue.put(repl,
                                    lambda: self._new_replications_window.update_success(ref),
                                    lambda err: self._new_replications_window.update_failed(ref, err))

    def set_selected_databases_limit(self, limit):
        selected_databases = [item for item in self._databases.selected if item.db_name[0] != '_']
        if len(selected_databases) > 0:
            def func():
                for row in selected_databases:
                    self._model.set_revs_limit(row.db_name, limit)
            self.couchdb_request(func)

    # region Properties
    @property
    def server(self):
        return self._connection_bar.server

    @property
    def port(self):
        return self._connection_bar.port

    @property
    def secure(self):
        return self._connection_bar.secure
    # endregion

    # region Event handlers
    def on_button_connect(self, button):
        self._model = None
        self._infobar_warnings.show(False)
        self._replication_tasks.clear()
        self._databases.clear()
        self._statusbar.reset()
        self._main_window_view_model.reset_window_titles()

        try:
            self._model = MainWindowModel(self.server, self.port, self.secure, self.get_credentials)

            def request():
                self._databases.update(self._model.databases)
                self._replication_tasks.update(self._model.replication_tasks)
                self._statusbar.update(self._model)
                self._main_window_view_model.update_window_titles(self._model)

            self.couchdb_request(request)
        except Exception as e:
            self.report_error(e)

    def on_infobar_warnings_response(self, widget, user_data):
        self._infobar_warnings.show(False)

    def on_menu_databases_refresh(self, menu):
        self._databases.update(self._model.databases)

    def on_comboboxtext_port_changed(self, widget):
        self._connection_bar.on_comboboxtext_port_changed()

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
                self._model.create_database(name)
                db = self._model.get_database(name)
                self._databases.append(db)
            self.couchdb_request(request)

    def on_menu_databases_delete(self, menu):
        selected_databases = [item for item in self._databases.selected if item.db_name[0] != '_']
        if len(selected_databases) > 0:
            result = self.delete_databases_dialog.run(selected_databases)
            if result == Gtk.ResponseType.OK:
                def request():
                    for db in reversed(self.delete_databases_dialog.selected_databases):
                        self._model.delete_database(db.db_name)
                        self._databases.remove(db.db_name)
                self.couchdb_request(request)

    def on_menu_databases_backup(self, menu):
        selected_databases = self._databases.selected
        if len(selected_databases) == 1 and selected_databases[0].db_name.find('backup$') < 0:
            backup_database = True
            source_name = selected_databases[0].db_name
            target_name = 'backup$' + source_name

            try:
                self._model.get_database(target_name)
                response = GtkHelper.run_dialog(self._win, Gtk.MessageType.QUESTION,
                                                Gtk.ButtonsType.YES_NO,
                                                "Target database already exists, continue?")

                backup_database = response is Gtk.ResponseType.YES
            except:
                pass

            if backup_database:
                repl = Replication(self._model, source_name, target_name, drop_first=True, create=True)
                self.queue_replication(repl)

    def on_menu_databases_restore(self, menu):
        selected_databases = self._databases.selected
        if len(selected_databases) == 1 and selected_databases[0].db_name.find('backup$') == 0:
            restore_database = True
            source_name = selected_databases[0].db_name
            target_name = source_name[7::]

            try:
                self._model.get_database(target_name)
                response = GtkHelper.run_dialog(self._win, Gtk.MessageType.QUESTION,
                                                Gtk.ButtonsType.YES_NO,
                                                "Target database already exists, continue?")

                restore_database = response is Gtk.ResponseType.YES
            except:
                pass

            if restore_database:
                repl = Replication(self._model, source_name, target_name, drop_first=True, create=True)
                self.queue_replication(repl)

    def on_menuitem_databases_compact(self, menu):
        selected_databases = self._databases.selected
        if len(selected_databases) == 1:
            def func():
                name = selected_databases[0].db_name
                self._model.compact_database(name)
            self.couchdb_request(func)

    def on_menu_databases_browse_futon(self, menu):
        selected_databases = self._databases.selected
        if len(selected_databases) > 0:
            url = '{0}://{1}:{2}/_utils/database.html?{3}'.format(
                'https' if self.secure else 'http',
                self.server, self.port, selected_databases[0].db_name)
            webbrowser.open_new_tab(url)

    def on_menu_databases_browse_fauxton(self, menu):
        selected_databases = self._databases.selected
        if len(selected_databases) > 0:
            url = '{0}://{1}:{2}/_utils/fauxton/index.html#/database/{3}/_all_docs?limit=20'.format(
                'https' if self.secure else 'http',
                self.server, self.port, selected_databases[0].db_name)
            webbrowser.open_new_tab(url)

    def on_menu_databases_browse_alldocs(self, menu):
        selected_databases = self._databases.selected
        if len(selected_databases) > 0:
            url = '{0}://{1}:{2}/{3}/_all_docs?limit=100'.format(
                'https' if self.secure else 'http',
                self.server, self.port, selected_databases[0].db_name)
            webbrowser.open_new_tab(url)

    def on_menuitem_databases_replication_new(self, menu):
        replications = None
        selected_databases = self._databases.selected
        selected_count = len(selected_databases)

        if selected_count == 1:
            db = selected_databases[0]
            # TODO: review
            result = self.new_single_replication_dialog.run(self._model.couchdb, db.db_name)
            if result == Gtk.ResponseType.OK:
                replications = self.new_single_replication_dialog.replications
        elif selected_count > 1:
            source_names = [db.db_name for db in selected_databases]
            # TODO: review
            result = self.new_multiple_replication_dialog.run(self._model.couchdb, source_names)
            if result == Gtk.ResponseType.OK:
                replications = self.new_multiple_replication_dialog.replications

        if replications:
            self.checkmenuitem_view_new_replication_window.set_active(True)
            for repl in replications:
                self.queue_replication(repl)

    def on_menuitem_databases_replication_remote(self, menu):
        replications = None
        # TODO: review
        result = self.remote_replication_dialog.run(self._model.couchdb)
        if result == Gtk.ResponseType.OK:
            replications = self.remote_replication_dialog.replications

        if replications:
            self.checkmenuitem_view_new_replication_window.set_active(True)
            for repl in replications:
                self.queue_replication(repl)

    def on_menu_databases_show(self, menu):
        connected = self._model is not None
        selected_databases = self._databases.selected
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
        self.menuitem_database_set_revisions_1.set_sensitive(single_row or multiple_rows)
        self.menuitem_database_set_revisions_10.set_sensitive(single_row or multiple_rows)
        self.menuitem_database_set_revisions_100.set_sensitive(single_row or multiple_rows)
        self.menuitem_database_set_revisions_1000.set_sensitive(single_row or multiple_rows)

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
        if self._model and info == 0:
            repl_count = 0
            this_url = self._model.couchdb.get_url()
            text = data.get_text()
            urls = text.split('\n')
            for url in urls:
                if re.search('^https?://', url) is not None and url.find(this_url) != 0:
                    u = urlparse(url)
                    if not (u.hostname == self.server and u.port == self.port):
                        target = u.path[1::]
                        repl = Replication(self._model, url, target, continuous=False, create=True)
                        self.queue_replication(repl)
                        repl_count += 1
            if repl_count:
                self.checkmenuitem_view_new_replication_window.set_active(True)

    def on_treeview_databases_drag_data_get(self, widget, drag_context, data, info, time):
        selected_databases = self._databases.selected
        selected_count = len(selected_databases)
        if selected_count > 0:
            text = ''
            url = self._model.url
            for db in selected_databases:
                if len(text) > 0:
                    text += '\n'
                text += url + db.db_name
            data.set_text(text, -1)

    def on_menuitem_help_about_activate(self, menu):
        self.about_dialog.run()

    def on_menuitem_database_set_revisions_1_activate(self, menu):
        self.set_selected_databases_limit(1)

    def on_menuitem_database_set_revisions_10_activate(self, menu):
        self.set_selected_databases_limit(10)

    def on_menuitem_database_set_revisions_100_activate(self, menu):
        self.set_selected_databases_limit(100)

    def on_menuitem_database_set_revisions_1000_activate(self, menu):
        self.set_selected_databases_limit(1000)
    # endregion
