class ResourceStorage:
    __slots__ = ('allows_incoming', 'allows_outgoing', 'capacity', '_storage')

    def __init__(
        self, allows_incoming: bool, allows_outgoing: bool, capacity: int
    ):
        self.allows_incoming = allows_incoming
        self.allows_outgoing = allows_outgoing
        self.capacity = capacity
        self._storage = []

    def add(self, item) -> bool:
        if len(self._storage) < self.capacity:
            self._storage.append(item)
            return True
        return False

    def available(self) -> int:
        return self.capacity - len(self._storage)

    def is_empty(self) -> bool:
        return len(self._storage) == 0

    def is_full(self) -> bool:
        return len(self._storage) == self.capacity

    def quantity(self) -> int:
        return len(self._storage)

    def pop(self) -> object:
        return self._storage.pop()

    def remove(self, item) -> object:
        return self._storage.remove(item)

    def __iter__(self):
        return iter(self._storage)
