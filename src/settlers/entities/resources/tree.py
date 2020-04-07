from . import Resource
from settlers.engine.components.generative import Generative
from settlers.engine.components.harvesting import (
    Harvestable
)


class Lumber(Resource):
    pass


class TreeLog(Resource):
    pass


class Tree(Resource):
    __slots__ = ['max_quantity', 'quantity']

    components = [(Harvestable, 'quantity', TreeLog, 3, 3, 1)]

    def __init__(self, quantity, max_quantity):
        super().__init__()

        self.quantity = quantity
        self.max_quantity = max_quantity

    def initialize(self):
        self.components.add(
            (Generative, 'quantity', -1, 4, 1, self.max_quantity)
        )

        super().initialize()

    def __repr__(self):
        return "<resources.{self} {id}>".format(
            self=self.__class__.__name__,
            id=hex(id(self)),
        )
