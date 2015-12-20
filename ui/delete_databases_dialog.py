from gi.repository import Gtk

from src.model_mapper import ModelMapper


class DeleteDatabasesDialog:
    _database_rows = None
    _selected_database_rows = None

    def __init__(self, builder):
        self._win = builder.get_object('dialog_delete_databases', target=self, include_children=True)

    def on_dialog_delete_databases_show(self, dialog):
        model = Gtk.ListStore(str, bool, object)
        for row in self._database_rows:
            mapper = ModelMapper(row, [lambda i=row: i.db.db_name, lambda i: True])
            model.append(mapper)
        self.treeview_delete_databases.set_model(model)
        model.connect('row-changed', self.on_row_changed)
        self.set_button_ok_active_state()

    def run(self, databases):
        self._database_rows = databases
        self._selected_database_rows = None

        result = self._win.run()
        self._win.hide()
        self._database_rows = None

        if result == Gtk.ResponseType.OK:
            self._selected_database_rows = self._get_selected_database_rows()

        return result

    def on_button_delete_databases_dialog_ok(self, button):
        self._win.response(Gtk.ResponseType.OK)

    def on_button_delete_databases_dialog_cancel(self, button):
        self._win.response(Gtk.ResponseType.CANCEL)

    def on_cellrenderertoggle_delete_toggled(self, widget, path):
        model = self.treeview_delete_databases.get_model()
        itr = model.get_iter(path)
        val = model.get_value(itr, 1)
        model.set(itr, 1, not val)

    def on_row_changed(self, model, path, iter):
        self.set_button_ok_active_state()

    @property
    def selected_database_rows(self):
        return self._selected_database_rows

    def _get_selected_database_rows(self):
        selected_databases = []
        model = self.treeview_delete_databases.get_model()
        itr = model.get_iter_first()
        while itr is not None:
            if model.get_value(itr, 1):
                path = model.get_path(itr)
                row = model[path]
                db = ModelMapper.get_item_instance(row)
                selected_databases.append(db)
            itr = model.iter_next(itr)
        return selected_databases

    def set_button_ok_active_state(self):
        sensitive = len(self._get_selected_database_rows()) > 0
        self.button_delete_databases_dialog_ok.set_sensitive(sensitive)
