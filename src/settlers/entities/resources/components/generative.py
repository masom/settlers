from settlers.entities.components import Component


class Generative(Component):
    __slots__ = [
        'cycles',
        'increase_per_cycle',
        'max_cycles'
        'max_value',
        'target_attr',
        'ticks',
        'ticks_per_cycle',
        'unlimited',
    ]

    def __init__(
        self, owner, target_attr, max_cycles, ticks_per_cycle,
        increase_per_cycle, max_value
    ):
        super().__init__(owner)

        self.cycles = 0
        self.increase_per_cycle = increase_per_cycle
        self.max_cycles = max_cycles
        self.unlimited = max_cycles < 0
        self.max_value = max_value
        self.ticks = 0
        self.target_attr = target_attr
        self.ticks_per_cycle = ticks_per_cycle

    def tick(self):
        value = getattr(self.owner, self.target_attr)
        if value >= self.max_value:
            return True

        if not self.unlimited and self.cycles > self.max_cycles:
            return False

        if self.ticks < self.ticks_per_cycle:
            self.ticks += 1
            return True

        self.cycles += 1
        self.ticks = 0

        value += 1

        print("{owner}#{self} increasing {attr} to {value}".format(
            attr=self.target_attr,
            owner=self.owner,
            self=self.__class__.__name__,
            value=value,
        ))
        setattr(self.owner, self.target_attr, value)
        return True
