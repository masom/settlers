from settlers.entities.components import Component


class EventMessage:
    __slots__ = ['event', 'interrupts', 'priority', 'type']

    def __init__(self, type, priority, interrupts, event):
        self.type = type
        self.priority = priority
        self.interrupts = interrupts
        self.event = event


class MessageQueue(Component):

    exposed_as = 'message_queue'
    exposed_methods = ['add', 'clear']

    __slots__ = ['_inbox']

    def __init__(self, owner):
        super()
        self._inbox = []

    def add(self, message):
        self._inbox.push(message)

    def clear(self):
        self._inbox = []

    def is_empty(self):
        self._inbox.size == 0

    def pop(self):
        self._inbox.pop(0)

    def peek(self, position: 0):
        self._inbox[position]

    def prioritize(self):
        pass
