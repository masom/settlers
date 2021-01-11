from typing import Dict, List, Type
from settlers.engine.components import Component
from settlers.engine.components.construction import (
    ConstructionSpec
)
from settlers.engine.components.factory import (
    Factory, Pipeline, PipelineInput, PipelineOutput
)
from settlers.engine.entities.resources import Resource
from settlers.engine.entities.position import Position
from settlers.entities.buildings.construction_site import (
    build_construction_site
)
from settlers.entities.resources.farming import (
    Beer, Bread, Ham, Soup, Vegetables
)
from settlers.entities.resources.stone import (
    Stone
)
from settlers.entities.resources.tree import (
    Lumber
)
from settlers.engine.entities.resources.resource_storage import ResourceStorage
from settlers.entities.buildings import Building

StoragesType = Dict[Type[Resource], ResourceStorage]


def build_brewery(name: str, components: List[Component]) -> Building:
    storages = brewery_storages()
    components = components + brewery_components(storages)

    brewery = Building(
        "{name}'s brewery".format(name=name),
        storages
    )

    for component in components:
        brewery.components.add(component)

    return brewery


def brewery_components(storages: StoragesType) -> list:
    return [
        (Factory, brewery_pipelines(storages), 1)
    ]


def brewery_storages() -> StoragesType:
    return {
        Beer: ResourceStorage(False, True, 30)
    }


def brewery_pipelines(storages: StoragesType) -> List[Pipeline]:
    return [
        Pipeline(
            [],
            PipelineOutput(1, Beer, storages[Beer]),
            10
        )
    ]


def build_brewery_construction_site(
    name: str, components: List[Component],
    position: Position
) -> Building:
    storages = brewery_storages()
    components = brewery_components(storages)

    spec = ConstructionSpec(
        components,
        [],
        {
            Lumber: 10,
            Stone: 10
        },
        4,
        1,
        "{name}'s brewery".format(name=name),
        storages
    )

    return build_construction_site(spec, [position])


def build_tavern(name: str, components: List[Component]) -> Building:
    storages = tavern_storages()

    # shop_items: Dict[Type[Resource], ResourceStorage] = {
    #     Beer: tavern_storages[Beer],
    #     Bread: tavern_storages[Bread],
    #     Soup: tavern_storages[Soup]
    # }

    tavern = Building(
        "{name}'s tavern".format(name=name),
        storages
    )

    components = components + tavern_components(storages)
    for component in components:
        tavern.components.add(component)

    return tavern


def tavern_components(pipelines: List[Pipeline]) -> list[tuple]:
    return [
        (Factory, pipelines, 1),
        # (Shop, shop_items, 1, 50)
    ]


def tavern_pipelines(storages: StoragesType) -> List[Pipeline]:
    return [
        Pipeline(
            [
                PipelineInput(1, Ham, storages[Ham]),
                PipelineInput(1, Vegetables, storages[Vegetables]),
            ],
            PipelineOutput(5, Soup, storages[Soup]),
            5
        )
    ]


def tavern_storages() -> List[StoragesType]:
    return {
        Beer: ResourceStorage(False, True, 40),
        Ham: ResourceStorage(True, False, 30),
        Soup: ResourceStorage(False, True, 30),
        Bread: ResourceStorage(True, False, 10),
        Vegetables: ResourceStorage(True, False, 10),
    }


def build_tavern_construction_site(
    name: str, components: List[Component],
    position: Position
) -> Building:
    storages = tavern_storages()
    components = tavern_components(storages)

    spec = ConstructionSpec(
        components,
        [],
        {
            Lumber: 10,
            Stone: 10
        },
        4,
        1,
        "{name}'s tavern".format(name=name),
        storages
    )

    return build_construction_site(spec, [position])
