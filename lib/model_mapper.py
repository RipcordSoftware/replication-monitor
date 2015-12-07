class ModelMapper:
    def __init__(self, item, mapper):
        self._item = item
        self._mapper = mapper
        self._mapper.append(self)

    @property
    def get_item(self):
        return self._item

    @property
    def get_mapper(self):
        return self._mapper

    def __getitem__(self, index):
        if index < 0 or index == len(self._mapper) - 1:
            return self._item
        else:
            val = self._mapper[index]

            if callable(val):
                return val(self._item)
            elif val is not None:
                return getattr(self._item, val)
            else:
                return None

    def __len__(self):
        return len(self._mapper)

    @staticmethod
    def get_item_instance(row):
        return row[-1]