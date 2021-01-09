from . import Resource
from settlers.engine.components.harvesting import (
    Harvestable
)
from settlers.entities.renderable import Renderable


class Stone(Resource):
    pass


class StoneSlab(Resource):
    pass


class StoneQuarry(Resource):
    __slots__ = ('quantity')

    components = [
        (Harvestable, 'quantity', StoneSlab, 4, 1, 2),
        (Renderable, 'stone_quarry')
    ]

    def __init__(self, quantity: int):
        super().__init__()

        self.quantity: int = quantity
