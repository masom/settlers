from settlers.engine.components import Component


class Renderable(Component):
    __slots__ = ['sprite', 'type', 'z']

    def __init__(self, owner, type, z=1):
        super().__init__(owner)

        self.sprite = None
        self.type = type
        self.z = z
