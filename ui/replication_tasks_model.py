import time

from ui.listview_model import ListViewModel


class ReplicationTasksModel(ListViewModel):
    def __init__(self):
        cols = (
            ListViewModel.ColDefinition('source', str),
            ListViewModel.ColDefinition('target', str),
            ListViewModel.ColDefinition(lambda row: '', str),
            ListViewModel.ColDefinition(lambda row: getattr(row, 'progress', None), int),
            ListViewModel.ColDefinition('continuous', bool),
            ListViewModel.ColDefinition(lambda row: time.strftime('%H:%M:%S', time.gmtime(row.started_on)), str),
            ListViewModel.ColDefinition(lambda row: time.strftime('%H:%M:%S', time.gmtime(row.updated_on)), str)
        )
        super().__init__(cols)