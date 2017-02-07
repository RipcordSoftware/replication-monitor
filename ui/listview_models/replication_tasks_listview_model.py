import time

from src.listview_model import ListViewModel


class ReplicationTasksListViewModel(ListViewModel):
    def __init__(self):
        cols = (
            ListViewModel.ColDefinition('source', str),
            ListViewModel.ColDefinition('target', str),
            ListViewModel.ColDefinition(lambda row: '', str),
            ListViewModel.ColDefinition(lambda row: getattr(row, 'progress', getattr(row, 'docs_written', None)), int),
            ListViewModel.ColDefinition('continuous', bool),
            ListViewModel.ColDefinition(lambda row: time.strftime('%H:%M:%S', time.gmtime(row.started_on)), str),
            ListViewModel.ColDefinition(lambda row: time.strftime('%H:%M:%S', time.gmtime(row.updated_on)), str)
        )
        super().__init__(cols)
