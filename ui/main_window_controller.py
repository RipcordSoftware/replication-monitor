from src.gtk_helper import GtkHelper

from ui.listview_model import ListViewModel
from ui.databases_model import DatabasesModel
from ui.replication_tasks_model import ReplicationTasksModel


class MainWindowController:
    def __init__(self):
        self._databases_model = ListViewModel.Sorted(DatabasesModel())

    @property
    def databases_model(self):
        return self._databases_model

    def update_databases(self, databases):
        def func():
            old_databases = {}
            new_databases = []
            model = self._databases_model

            itr = model.get_iter_first()
            while itr is not None:
                db = model[itr]
                old_databases[db.db_name] = model.get_path(itr)
                itr = model.iter_next(itr)

            for db in databases:
                i = old_databases.pop(db.db_name, None)
                if i is not None:
                    model[i] = db
                else:
                    new_databases.append(db)

            deleted_database_paths = [path for path in old_databases.values()]
            for path in reversed(deleted_database_paths):
                itr = model.get_iter(path)
                model.remove(itr)

            for db in new_databases:
                model.append(db)

        GtkHelper.invoke(func, async=False)
