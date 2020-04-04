import pathlib
import pdb
import sys

work_dir = pathlib.Path(__file__).resolve().parent.parent
src_path = work_dir / 'src'

sys.path.append(str(src_path))

from settlers.entities.buildings import Building
from settlers.entities.buildings.components.occupancy import Occupancy
from settlers.entities.buildings.components.transformer import (
    Transformer, Pipeline, PipelineInput, PipelineOutput, Storage
)

from settlers.entities.characters.components.worker import Worker
from settlers.entities.characters.components.harvester import Harvester
from settlers.entities.characters.villager import Villager

from settlers.entities.resources.tree import Tree, TreeLog, Lumber


bob = Villager()
sarah = Villager()

villagers = [
    bob,
    sarah,
]

tree = Tree(5, 100)

sawmill_tree_logs_store = Storage(50)
sawmill_tree_logs_store.add(TreeLog())
sawmill_tree_logs_store.add(TreeLog())

sawmill_pipelines = [
    Pipeline(
        [
            PipelineInput(1, TreeLog, sawmill_tree_logs_store)
        ],
        PipelineOutput(5, Lumber),
        Storage(8),
        2
    )
]

sawmill = Building()
sawmill.components.add((Occupancy, 1))
sawmill.components.add((Transformer, sawmill_pipelines))

buildings = [
    sawmill,
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

for entity in entities:
    entity.initialize()

# villager.harvesting.harvest(tree)
villagers[0].working.work_at(sawmill)
villagers[1].harvesting.harvest(tree)

sawmill.transform.start()

for tick in range(max_ticks):
    print("Tick={tick}".format(tick=tick))
    for entity in entities:
        entity.tick()
