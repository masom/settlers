import structlog
from typing import Dict, List, Optional, Set, Type

from settlers.engine.components import Component
from settlers.engine.entities.resources import Resource
from settlers.engine.entities.resources.resource_storage import ResourceStorage


logger = structlog.get_logger('engine.inventory_routing')


class InventoryRouting(Component):

    __slots__ = ('building', 'priority_list')

    exposed_as = 'inventory'
    exposed_methods = (
        'available_for_transport',
        'can_receive_resources',
        'receive_resource',
        'remove_inventory',
        'storage_for',
        'wants_resources'
    )

    def __init__(self, owner, priority_list: list):
        super().__init__(owner)
        self.priority_list = priority_list

    def available_for_transport(
        self, requested_resources: List[Type[Resource]] = []
    ) -> Optional[Type[Resource]]:
        storages: Dict[Type[Resource], ResourceStorage] = self.owner.storages
        building_resources: Set[Resource] = set([
            r for (r, s) in storages.items()
            if s.allows_outgoing
        ])

        common: Optional[set] = None
        if requested_resources:
            requested_resource_keys = set(requested_resources)
            common = requested_resource_keys.intersection(building_resources)

            if not common:
                return None

        if common:
            transportable = common
        else:
            transportable = building_resources

        available: Dict[Type[Resource], bool] = {}
        for resource in transportable:
            storage = storages[resource]
            if storage.allows_outgoing:
                available[resource] = not storage.is_empty()
            else:
                available[resource] = False

        for item in transportable:
            if available[item]:
                return item

    def can_receive_resources(self) -> bool:
        if len(self.owner.storages) == 0:
            return False

        for storage in self.owner.storages.values():
            if not storage.allows_incoming:
                return False
            return not storage.is_full()

        return False

    def receive_resource(self, resource: Type[Resource]) -> bool:
        storage: Optional[ResourceStorage] = self.owner.storages[
            resource.__class__
        ]

        if storage is None:
            return False

        if not storage.allows_incoming:
            return False

        if storage.is_full():
            return False

        return storage.add(resource)

    def storage_for(
        self, resource: Type[Resource]
    ) -> Optional[ResourceStorage]:
        for stored_resource, storage in self.owner.storages.items():
            if stored_resource == resource.__class__:
                return storage

    def remove_inventory(
        self, item: Type[Resource]
    ) -> Optional[Type[Resource]]:
        storage = self.owner.storages[item]
        if not storage.allows_outgoing:
            return None

        if storage.is_empty():
            return None

        return storage.pop()

    def wants_resources(self) -> List[Type[Resource]]:
        return [
            resource
            for resource, storage in self.owner.storages.items()
            if storage.allows_incoming and not storage.is_full()
        ]
