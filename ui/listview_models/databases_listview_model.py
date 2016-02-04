import re

from src.listview_model import ListViewModel


class DatabasesListViewModel(ListViewModel):
    def __init__(self):
        cols = (
            ListViewModel.ColDefinition('db_name', str),
            ListViewModel.ColDefinition('doc_count', int),
            ListViewModel.ColDefinition(lambda row: self._get_update_sequence(row.update_seq), int),
            ListViewModel.ColDefinition(lambda row: int(round(row.disk_size / 1024 / 1024)), int),
            ListViewModel.ColDefinition(lambda row: 'Yes' if getattr(row, 'compact_running', False) else 'No', str),
            ListViewModel.ColDefinition('revs_limit', int)
        )
        super().__init__(cols)

    @staticmethod
    def _get_update_sequence(val):
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
