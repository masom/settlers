import pathlib
import pdb
import sys
import names

work_dir = pathlib.Path(__file__).resolve().parent.parent
src_path = work_dir / 'src'

sys.path.append(str(src_path))

from settlers.entities.buildings import Building
from settlers.entities.buildings.components.construction import (
    Construction, ConstructionSpec
)
from settlers.entities.buildings.components.occupancy import Occupancy
from settlers.entities.buildings.components.transformer import (
    Transformer, Pipeline, PipelineInput, PipelineOutput
)

from settlers.entities.components.mouvement import Mouvement
from settlers.entities.characters.components.builder import (
    Builder, BUILDER_ABILITY_CARPENTER
)
from settlers.entities.characters.components.harvester import Harvester
from settlers.entities.characters.components.transport import Transport
from settlers.entities.characters.components.worker import Worker
from settlers.entities.characters.villager import Villager

from settlers.entities.resources import Storage
from settlers.entities.resources.tree import Tree, TreeLog, Lumber


def build_construction_site(spec):
    storages = {}

    for resource, quantity in spec.construction_resources.items():
        storages[resource] = Storage(True, False, quantity)

    construction_site = Building(
        spec.name,
        storages,
    )

    construction_site.components.add(
        (Construction, spec)
    )

    return construction_site


def build_sawmill_construction_site(name):
    sawmill_storages = {
        TreeLog: Storage(True, False, 10),
        Lumber: Storage(False, True, 50),
    }

    sawmill_pipelines = [
        Pipeline(
            [
                PipelineInput(1, TreeLog, sawmill_storages[TreeLog])
            ],
            PipelineOutput(5, Lumber, sawmill_storages[Lumber]),
            2
        )
    ]

    return build_construction_site(ConstructionSpec(
        [
            (Occupancy, 1),
            (Transformer, sawmill_pipelines)
        ],
        [
            BUILDER_ABILITY_CARPENTER
        ],
        {
            Lumber: 10,
        },
        4,
        "Jello's Sawmill",
        sawmill_storages
    ))


def build_sawmill(name):
    sawmill_storages = {
        TreeLog: Storage(True, False, 10),
        Lumber: Storage(False, True, 50),
    }

    sawmill_pipelines = [
        Pipeline(
            [
                PipelineInput(1, TreeLog, sawmill_storages[TreeLog])
            ],
            PipelineOutput(5, Lumber, sawmill_storages[Lumber]),
            2
        )
    ]

    sawmill = Building(
        "{name}'s Sawmill".format(name=name),
        sawmill_storages
    )

    sawmill.components.add((Occupancy, 1))
    sawmill.components.add((Transformer, sawmill_pipelines))

    return sawmill


sawmill = build_sawmill('Bob')
construction_site = build_sawmill_construction_site('Jello')

tree = Tree(5, 100)

buildings = [
    sawmill,
    construction_site
]

resources = [
    tree,
]

entities = []
entities.extend(buildings)
entities.extend(resources)

max_ticks = 30

villagers = []
for i in range(4):
    name = names.get_full_name()
    villager = Villager(name)
    transport_storage = Storage(True, True, 5)

    transport_resources = {
        TreeLog: transport_storage,
        Lumber: transport_storage,
    }

    villager.components.add((Harvester, [TreeLog], transport_storage))
    villager.components.add(Worker)
    villager.components.add((Builder, [BUILDER_ABILITY_CARPENTER]))
    villager.components.add((Transport, transport_resources))

    villagers.append(villager)

entities.extend(villagers)

for entity in entities:
    entity.initialize()

villagers[0].harvesting.harvest(tree)
villagers[0].harvesting.assign_destination(sawmill)
villagers[1].working.work_at(sawmill)

villagers[2].construction.build(construction_site)
villagers[3].transport.pickup_from(sawmill)
villagers[3].transport.assign_destination(construction_site)

sawmill.transform.start()

for tick in range(max_ticks):
    print("##### Tick={tick} #####".format(tick=tick))
    for entity in entities:
        entity.tick()
