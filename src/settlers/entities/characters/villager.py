from .character import Character

from settlers.entities.components.mouvement import Mouvement


class Villager(Character):
    components = [Mouvement]
