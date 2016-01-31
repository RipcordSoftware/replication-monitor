from src.gtk_helper import GtkHelper
from src.listview_model import ListViewModel

from ui.listview_models.replication_tasks_listview_model import ReplicationTasksListViewModel


class ReplicationTasksViewModel:
    def __init__(self, listview):
        self._listview = listview
        self._model = ReplicationTasksListViewModel()
        self._sorted_model = ListViewModel.Sorted(self._model)
        self._listview.set_model(self._sorted_model)

    @GtkHelper.invoke_func
    def update(self, tasks):
        old_tasks = {}
        new_tasks = []

        itr = self._model.get_iter_first()
        while itr is not None:
            task = self._model[itr]
            old_tasks[task.replication_id] = self._model.get_path(itr)
            itr = self._model.iter_next(itr)

        for task in tasks:
            i = old_tasks.pop(task.replication_id, None)
            if i is not None:
                self._model[i] = task
            else:
                new_tasks.append(task)

        deleted_replication_task_paths = [path for path in old_tasks.values()]
        for path in sorted(deleted_replication_task_paths, reverse=True):
            itr = self._model.get_iter(path)
            self._model.remove(itr)

        for task in new_tasks:
            self._model.append(task)

    @GtkHelper.invoke_func
    def clear(self):
        self._model.clear()
