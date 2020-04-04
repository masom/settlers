import pathlib
import pdb
import sys

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
from settlers.entities.characters.components.worker import Worker
from settlers.entities.characters.villager import Villager

from settlers.entities.resources import Storage
from settlers.entities.resources.tree import Tree, TreeLog, Lumber


bob = Villager()
sarah = Villager()

villagers = [
    bob,
    sarah,
]

tree = Tree(5, 100)


def build_construction_site(spec):
    storages = {}

    for resource, quantity in spec.construction_resources.items():
        storages[resource] = Storage(quantity)

    construction_site = Building(
        "{name}'s #{target}",
        storages,
    )

    construction_site.components.add(
        (Construction, spec)
    )

    return construction_site


def build_sawmill_construction_site(name):
    sawmill_storages = {
        TreeLog: Storage(50),
        Lumber: Storage(8),
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
        10,
        'Jello',
        sawmill_storages
    ))


def build_sawmill(name):
    sawmill_storages = {
        TreeLog: Storage(50),
        Lumber: Storage(8),
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
entities.extend(villagers)

max_ticks = 60

for villager in villagers:
    villager.components.add((Harvester, [TreeLog], Storage(1)))
    villager.components.add(Worker)
    villager.components.add((Builder, [BUILDER_ABILITY_CARPENTER]))

for entity in entities:
    entity.initialize()

# villager.harvesting.harvest(tree)
villagers[0].working.work_at(sawmill)
villagers[1].harvesting.assign_destination(sawmill)
villagers[1].harvesting.harvest(tree)

sawmill.transform.start()

for tick in range(max_ticks):
    print("##### Tick={tick} #####".format(tick=tick))
    for entity in entities:
        entity.tick()
