import pathlib
import pdb
import sys

work_dir = pathlib.Path(__file__).resolve().parent.parent
src_path = work_dir / 'src'

sys.path.append(str(src_path))

from settlers.entities.resources.tree import Tree

entities = [
    Tree(5, 100),
    Tree(0, 20)
]

max_ticks = 5

for entity in entities:
    entity.initialize()

for tick in range(max_ticks):
    print("Tick={tick}".format(tick=tick))
    for entity in entities:
        entity.tick()
