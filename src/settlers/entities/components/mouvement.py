from settlers.entities.components import Component


class Mouvement(Component):
    DIRECTION_UP = 'up'
    DIRECTION_DOWN = 'down'
    DIRECTION_LEFT = 'left'
    DIRECTION_RIGHT = 'right'

    movements_per_seconds = 1.0

    directions = [
        DIRECTION_UP,
        DIRECTION_DOWN,
        DIRECTION_LEFT,
        DIRECTION_RIGHT
    ]

    def move(self, direction):
        if direction in self.directions:
            self.position.update(direction)
        else:
            raise
