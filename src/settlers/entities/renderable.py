from settlers.engine.components import Component
import structlog

logger = structlog.get_logger("engine.renderable")

class Renderable(Component):
    __slots__ = ('sprite', 'type', 'z')

    exposed_as = 'renderable'
    exposed_methods = ('reset_sprite')

    def __init__(self, owner, type: str, z: int = 1) -> None:
        super().__init__(owner)

        self.sprite = None
        self.type = type
        self.z = z

    def reset_sprite(self, new_type: str) -> None:
        logger.debug(
            'reset_sprite',
            owner=self.owner,
        )

        self.sprite = None
        self.type = new_type


    def __repr__(self) -> str:
        return "<{owner}#{component} {id}>".format(
            owner=self.owner,
            component=self.__class__.__name__,
            id=hex(id(self))
        )
