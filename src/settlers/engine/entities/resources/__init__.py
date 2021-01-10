from settlers.engine.entities.entity import Entity


class Resource(Entity):
    def __repr__(self) -> str:
        return "<resources.{self} {id}>".format(
            self=self.__class__.__name__,
            id=hex(id(self)),
        )
