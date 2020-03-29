from settlers.entities.resources import Resource
from settlers.entities.resources.components.generative import Generative
from settlers.entities.resources.components.harvestable import Harvestable


class Tree(Resource):
    __slots__ = ['max_quantity', 'quantity']

    components = [(Harvestable, 'quantity', 3, 1, 1)]

    def __init__(self, quantity, max_quantity):
        self.quantity = self.quantity
        self.max_quantity = max_quantity

    def initialize(self):
        self.components.push(
            Generative(
                self,
                'quantity',
                -1,
                5,
                1,
                self.max_quantity
            ),
        )

        super()
