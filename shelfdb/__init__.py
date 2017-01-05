import asyncio, shelve, os, uuid
from datetime import datetime
from itertools import islice


class Shelf(dict):
    def __init__(self, db_dir=None, *args, **kw):
        if db_dir is None:
            db_dir = os.path.join(os.getcwd(), 'db')
        self.dir = db_dir
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
        return super().__init__(*args, **kw)

    def __getitem__(self, k):
        if (not k in self or
                isinstance(super().__getitem__(k)._shelf.dict, shelve._ClosedDict)):
            shelf = shelve.open(os.path.join(self.dir, k))
            super().__setitem__(
                k, ShelfQuery(shelf))
        return super().__getitem__(k)

    def get(self, k):
        return self.__getitem__(k)

    def close(self):
        for k in self:
            self[k].close()


class ShelfQuery():
    def __init__(self, shelf):
        self._shelf = shelf

    def __iter__(self):
        return map(self._get_entry, self._shelf.items())

    def __getitem__(self, id_):
        entry = self._shelf[id_]
        return Entry(self._shelf, id_, entry)

    def _get_entry(self, item):
        return Entry(self._shelf, item[0], item[1])

    def first(self, filter_):
        try:
            return next(filter(filter_, self))
        except StopIteration:
            return None

    def filter(self, filter_):
        return ChainQuery(filter(filter_, self))

    def slice(self, start, stop, step=None):
        return ChainQuery(islice(self, start, stop))

    def sort(self, key=lambda entry: entry['_id'], reverse=False):
        return ChainQuery(iter(sorted(self, key=key, reverse=reverse)))

    def update(self, patch):
        [entry.update(patch) for entry in self]

    def insert(self, entry):
        # Since id_=str(uuid.uuid1()) in def args will return the same value
        id_ = str(uuid.uuid1())
        if isinstance(entry, dict):
            self._shelf[id_] = entry
            return id_
        else:
            raise Exception('Entry is not a dict object')

    def put(self, id_, entry):
        if isinstance(entry, dict):
            self._shelf[id_] = entry
            return id_
        else:
            raise Exception('Entry is not a dict object')

    def replace(self, data):
        for entry in self:
            entry.replace(data)

    def delete(self):
        for entry in self:
            del self._shelf[entry['_id']]

class ChainQuery(ShelfQuery):
    def __init__(self, results):
        self._results = results

    def __iter__(self):
        return self._results

class Entry(dict):
    def __init__(self, shelf, id_, entry):
        self._shelf = shelf
        self._id = id_
        super().__init__(entry)
        super().__setitem__('_id', id_)

    def update(self, patch):
        super().update(patch)
        entry = dict(self)
        del entry['_id']
        self._shelf[self._id] = entry

    def pop(self, k):
        super().pop(k)
        entry = dict(self)
        del entry['_id']
        self._shelf[self._id] = entry

    def replace(self, entry):
        self.clear()
        self.__init__(self._shelf, self._id, entry)
        entry = dict(self)
        del entry['_id']
        self._shelf[self._id] = entry

    def delete(self):
        del self._shelf[self._id]
