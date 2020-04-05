from settlers.entities import Entity


class Resource(Entity):
    pass


class Storage:
    __slots__ = ['capacity', '_storage']

    def __init__(self, capacity):
        self.capacity = capacity
        self._storage = []

    def add(self, item):
        if len(self._storage) < self.capacity:
            self._storage.append(item)
            return True
        return False

    def is_empty(self):
        return len(self._storage) == 0

    def is_full(self):
        return len(self._storage) == self.capacity

    def quantity(self):
        return len(self._storage)

    def pop(self):
        return self._storage.pop()

    def remove(self, item):
        return self._storage.remove(item)

    def __iter__(self):
        return iter(self._storage)
