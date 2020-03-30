import pathlib
import pdb
import sys

work_dir = pathlib.Path(__file__).resolve().parent.parent
src_path = work_dir / 'src'

sys.path.append(str(src_path))

from settlers.entities.buildings import Building
from settlers.entities.buildings.components.transformer import (
    Transformer, Pipeline, PipelineInput, Storage
)

from settlers.entities.characters.components.worker import Worker
from settlers.entities.characters.components.harvester import Harvester
from settlers.entities.characters.villager import Villager

from settlers.entities.resources.tree import Tree, TreeLog, Lumber


villager = Villager()
tree = Tree(5, 100)

sawmill_pipelines = [
    Pipeline(
        [
            PipelineInput(TreeLog, Storage(50))
        ],
        Lumber,
        Storage(2),
        2
    )
]

sawmill = Building()
sawmill.components.add((Transformer, sawmill_pipelines))

entities = [
    sawmill,
    # tree,
    # Tree(0, 20),
    villager
]

max_ticks = 60

for entity in entities:
    entity.initialize()

villager.components.add(Harvester)
villager.components.add(Worker)
# villager.harvesting.harvest(tree)
villager.working.work_at(sawmill)
sawmill.transform.start()

for tick in range(max_ticks):
    print("Tick={tick}".format(tick=tick))
    for entity in entities:
        entity.tick()
