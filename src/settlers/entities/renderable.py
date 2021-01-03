from settlers.engine.components import Component


class Renderable(Component):
    __slots__ = ['sprite', 'type', 'z']

    exposed_as = 'renderable'
    exposed_methods = ('reset_sprite')

    def __init__(self, owner, type: str, z: int = 1) -> None:
        super().__init__(owner)

        self.sprite = None
        self.type = type
        self.z = z

    def reset_sprite(self):
        self.sprite = None
