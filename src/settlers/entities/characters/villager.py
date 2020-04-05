from .character import Character

from settlers.entities.components.mouvement import Mouvement


class Villager(Character):
    __slots__ = ['name']
    components = [Mouvement]

    def __init__(self, name):
        super().__init__()
        self.name = name
