from gi.repository import GObject
from gi.repository import Gtk


class ListViewModel(GObject.Object, Gtk.TreeModel):
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

    class Sorted(Gtk.TreeModelSort, Gtk.TreeDragDest, Gtk.TreeDragSource):
        def __init__(self, child_model):
            super().__init__(child_model)
            self._attach_sort_functions(child_model)

        def __getitem__(self, item):
            return self.get_model()[item]

        def __setitem__(self, key, value):
            self.get_model()[key] = value

        def append(self, row):
            return self.get_model().append(row)

        def remove(self, it):
            return self.get_model().remove(it)

        def clear(self):
            return self.get_model().clear()

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

        # region Event overrides
        def do_drag_data_delete(self, path):
            do_drag_data_delete = getattr(super().get_model(), 'do_drag_data_delete', None)
            return do_drag_data_delete(path) if callable(do_drag_data_delete) else False

        def do_drag_data_get(self, path, selection):
            do_drag_data_get = getattr(super().get_model(), 'do_drag_data_get', None)
            if callable(do_drag_data_get):
                do_drag_data_get(path, selection)

        def do_row_draggable(self, path):
            do_row_draggable = getattr(super().get_model(), 'do_row_draggable', None)
            return do_row_draggable(path) if callable(do_row_draggable) else False

        def get_iter_first(self):
            return self.get_model().get_iter_first()

        def get_iter(self, path):
            return self.get_model().get_iter(path)

        def iter_next(self, it):
            return self.get_model().iter_next(it)

        def get_path(self, it):
            return self.get_model().get_path(it)
        # endregion

    def __init__(self, cols):
        super().__init__()
        self._cols = cols
        self._data = []

    def __getitem__(self, item):
        index = self._get_index(item)
        return self._data[index]

    def __setitem__(self, key, value):
        index = self._get_index(key)
        self._data[index] = value

        it = self._get_iter(index)
        super().emit('row-changed', self.do_get_path(it), it)

    def append(self, row):
        self._data.append(row)
        it = self._get_iter(len(self._data) - 1)
        super().row_inserted(self.do_get_path(it), it)

    def remove(self, it):
        super().row_deleted(self.do_get_path(it))
        index = self._get_index(it)
        self._data.pop(index)

    def clear(self):
        for index in range(len(self._data) - 1, -1, -1):
            path = self._get_path(index)
            super().row_deleted(path)
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

    def get_iter_first(self):
        it = None
        if len(self._data) > 0:
            it = self._get_iter(0)
        return it

    def do_get_iter(self, path):
        # Return False and an empty iter when out of range
        index = path.get_indices()[0]
        if index < 0 or index >= len(self._data):
            return False, None

        it = self._get_iter(index)
        return True, it

    def do_get_path(self, it):
        return self._get_path(it)

    def do_get_value(self, it, column):
        index = self._get_index(it)
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
        next = self._get_index(it) + 1
        if next >= len(self._data):
            return False

        # Set the iters data and return True
        it.user_data = next
        return True

    def do_iter_previous(self, it):
        prev = self._get_index(it) - 1
        if prev < 0:
            return False

        it.user_data = prev
        return True

    def do_iter_children(self, parent):
        # If parent is None return the first item
        if parent is None:
            it = self._get_iter(0)
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
            it = self._get_iter(n)
            return True, it

    def do_iter_parent(self, child):
        return False, None

    def do_drag_data_delete(self):
        return False

    def do_drag_data_get(self, path, selection):
        pass

    def do_row_draggable(self, path):
        return True
    # endregion

    # region Static methods
    @staticmethod
    def _get_index(value):
        index = value
        if isinstance(value, str):
            index = int(value)
        elif isinstance(value, Gtk.TreePath):
            index = value.get_indices()[0]
        elif isinstance(value, Gtk.TreeIter):
            index = value.user_data
        return index

    @staticmethod
    def _get_iter(value):
        it = Gtk.TreeIter()
        if isinstance(value, str):
            it.user_data = int(value)
        elif isinstance(value, Gtk.TreePath):
            it.user_data = value.get_indices()[0]
        elif isinstance(value, int):
            it.user_data = value
        return it

    @staticmethod
    def _get_path(value):
        path = None
        if isinstance(value, str):
            path = Gtk.TreePath((int(str),))
        elif isinstance(value, Gtk.TreeIter):
            path = Gtk.TreePath((ListViewModel._get_index(value),))
        elif isinstance(value, int):
            path = Gtk.TreePath((value,))
        return path
    # endregion
