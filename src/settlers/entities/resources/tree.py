from settlers.engine.entities.resources import Resource
from settlers.engine.components.generative import Generative
from settlers.engine.components.harvesting import (
    Harvestable
)
from settlers.entities.renderable import Renderable


class Lumber(Resource):
    pass


class TreeLog(Resource):
    pass


class Tree(Resource):
    __slots__ = ('max_quantity', 'quantity')

    components = [
        (Harvestable, 'quantity', TreeLog, 3, 3, 1),
        (Renderable, 'tree')
    ]

    def __init__(self, quantity: int, max_quantity: int):
        super().__init__()

        self.quantity = quantity
        self.max_quantity = max_quantity

    def initialize(self) -> None:
        self.components.add(
            (Generative, 'quantity', -1, 4, 1, self.max_quantity)
        )

        super().initialize()
