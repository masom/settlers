from settlers.entities import Entity
from settlers.entities.components.message_queue import MessageQueue


class Character(Entity):
    components = [MessageQueue]
