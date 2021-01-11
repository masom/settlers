from typing import Dict, List, Type

from settlers.engine.entities.resources import Resource


class ResourceStorage:
    __slots__ = (
        'allows_incoming',
        'allows_outgoing',
        'capacity',
        'priority',
        '_storage',
    )

    def __init__(
        self, allows_incoming: bool, allows_outgoing: bool, capacity: int,
        priority: int = 1
    ):
        self.allows_incoming = allows_incoming
        self.allows_outgoing = allows_outgoing
        self.capacity = capacity
        self.priority = min(priority, 3)
        self._storage: List[Resource] = []

    def add(self, item: Resource) -> bool:
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

    def pop(self) -> Resource:
        return self._storage.pop()

    def remove(self, item: Resource) -> Resource:
        return self._storage.remove(item)

    def __iter__(self) -> iter:
        return iter(self._storage)


ResourceStoragesType = Dict[Type[Resource], ResourceStorage]
