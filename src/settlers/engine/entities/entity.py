from ..components import Components


class Entity:
    def __init__(self) -> None:
        self.components: Components = Components(self)

    def initialize(self) -> None:
        self.components.initialize()
