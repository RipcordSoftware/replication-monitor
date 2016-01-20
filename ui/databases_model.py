import re

from gi.repository import GObject
from gi.repository import Gtk


class DatabasesModel(GObject.Object, Gtk.TreeModel):
    class ColDefinition:
        def __init__(self, name, col_type):
            self._name = name
            self._type = col_type

        @property
        def name(self):
            return self._name

        @property
        def type(self):
            return self._type

        @property
        def compare(self):
            def compare_strings(a, b):
                return -1 if a < b else 1 if a > b else 0
            return compare_strings if self.type == str else None

    class Sorted(Gtk.TreeModelSort):
        def __init__(self, child_model=None):
            child_model = DatabasesModel() if child_model is None else child_model
            super().__init__(child_model)
            self._attach_sort_functions(child_model)

        def append(self, row):
            self.get_model().append(row)

        def remove(self, it):
            self.get_model().remove(it)

        def clear(self):
            self.get_model().clear()

        def _attach_sort_functions(self, child_model):
            for (i, item) in enumerate(child_model.cols):
                if item.compare is not None:
                    def compare_cols(compare, name):
                        def callback(m, it_x, it_y, _):
                            x = child_model[it_x]
                            y = child_model[it_y]
                            return compare(getattr(x, name), getattr(y, name))
                        return callback
                    super().set_sort_func(i, compare_cols(item.compare, item.name))

    def __init__(self):
        super().__init__()
        self._cols = (
            self.ColDefinition('db_name', str),
            self.ColDefinition('doc_count', int),
            self.ColDefinition(lambda row: self._get_update_sequence(row.update_seq), int),
            self.ColDefinition(lambda row: int(round(row.disk_size / 1024 / 1024)), int),
            self.ColDefinition(lambda row: 'Yes' if row.compact_running else 'No', str),
            self.ColDefinition('revs_limit', int)
        )
        self._data = []

    def __getitem__(self, item):
        index = item
        if isinstance(item, str):
            index = int(item)
        elif isinstance(item, Gtk.TreePath):
            index = item.get_indices()[0]
        elif isinstance(item, Gtk.TreeIter):
            index = item.user_data
        return self._data[index]

    def __setitem__(self, key, value):
        index = key
        if isinstance(key, str):
            index = int(key)
        elif isinstance(key, Gtk.TreePath):
            index = key.get_indices()[0]
        elif isinstance(key, Gtk.TreeIter):
            index = key.user_data
        self._data[index] = value

        it = Gtk.TreeIter()
        it.user_data = index
        super().emit('row-changed', self.do_get_path(it), it)

    def append(self, row):
        self._data.append(row)
        it = Gtk.TreeIter()
        it.user_data = len(self._data) - 1
        super().row_inserted(self.do_get_path(it), it)

    def remove(self, it):
        super().row_deleted(self.do_get_path(it))
        index = it.user_data
        self._data.remove(index)

    def clear(self):
        it = Gtk.TreeIter()
        for index in range(len(self._data) - 1, -1, -1):
            it.user_data = index
            super().row_deleted(self.do_get_path(it))
        self._data.clear()

    @property
    def cols(self):
        return self._cols

    @property
    def rows(self):
        return self._data

    # region Model overrides
    def do_get_flags(self):
        return Gtk.TreeModelFlags.LIST_ONLY

    def do_get_n_columns(self):
        return len(self._cols)

    def do_get_column_type(self, n):
        return self._cols[n].type

    def do_get_iter(self, path):
        # Return False and an empty iter when out of range
        index = path.get_indices()[0]
        if index < 0 or index >= len(self._data):
            return False, None

        it = Gtk.TreeIter()
        it.user_data = index
        return True, it

    def do_get_path(self, it):
        return Gtk.TreePath([it.user_data])

    def do_get_value(self, it, column):
        index = it.user_data
        row = self._data[index]
        name = self._cols[column].name
        func = name if callable(name) else None
        if func:
            value = func(row)
        else:
            value = getattr(row, name, None)
        return value

    def do_iter_next(self, it):
        # Return False if there is not a next item
        next = it.user_data + 1
        if next >= len(self._data):
            return False

        # Set the iters data and return True
        it.user_data = next
        return True

    def do_iter_previous(self, it):
        prev = it.user_data - 1
        if prev < 0:
            return False

        it.user_data = prev
        return True

    def do_iter_children(self, parent):
        # If parent is None return the first item
        if parent is None:
            it = Gtk.TreeIter()
            it.user_data = 0
            return True, it
        return False, None

    def do_iter_has_child(self, it):
        return it is None

    def do_iter_n_children(self, it):
        # If iter is None, return the number of top level nodes
        if it is None:
            return len(self._data)
        return 0

    def do_iter_nth_child(self, parent, n):
        if parent is not None or n >= len(self._data):
            return False, None
        elif parent is None:
            # If parent is None, return the nth iter
            it = Gtk.TreeIter()
            it.user_data = n
            return True, it

    def do_iter_parent(self, child):
        return False, None
    # endregion

    # region Static methods
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
    # endregion
