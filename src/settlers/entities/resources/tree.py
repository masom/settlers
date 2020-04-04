from settlers.entities.resources import Resource
from settlers.entities.resources.components.generative import Generative
from settlers.entities.resources.components.harvestable import Harvestable


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
