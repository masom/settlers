from .character import Character

from settlers.entities.components.message_queue import MessageQueue
from settlers.entities.components.mouvement import Mouvement


class Villager(Character):
    components = [MessageQueue, Mouvement]
