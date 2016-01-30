from src.gtk_helper import GtkHelper

from ui.listview_model import ListViewModel
from ui.databases_model import DatabasesModel
from ui.replication_tasks_model import ReplicationTasksModel


class MainWindowController:
    def __init__(self):
        self._databases_model = ListViewModel.Sorted(DatabasesModel())
        self._replication_tasks_model = ListViewModel.Sorted(ReplicationTasksModel())

    @property
    def databases_model(self):
        return self._databases_model

    @property
    def replication_tasks_model(self):
        return self._replication_tasks_model

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

    def update_replication_tasks(self, tasks):
        def func():
            old_tasks = {}
            new_tasks = []
            model = self._replication_tasks_model

            itr = model.get_iter_first()
            while itr is not None:
                task = model[itr]
                old_tasks[task.replication_id] = model.get_path(itr)
                itr = model.iter_next(itr)

            for task in tasks:
                i = old_tasks.pop(task.replication_id, None)
                if i is not None:
                    model[i] = task
                else:
                    new_tasks.append(task)

            deleted_replication_task_paths = [path for path in old_tasks.values()]
            for path in sorted(deleted_replication_task_paths, reverse=True):
                itr = model.get_iter(path)
                model.remove(itr)

            for task in new_tasks:
                model.append(task)

        GtkHelper.invoke(func, async=False)
