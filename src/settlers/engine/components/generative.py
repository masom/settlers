import structlog

from . import Component

logger = structlog.get_logger('factory')


class Generative(Component):
    __slots__ = [
        'cycles',
        'increase_per_cycle',
        'max_cycles',
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
        self.max_value = max_value
        self.target_attr = target_attr
        self.ticks = 0
        self.ticks_per_cycle = ticks_per_cycle
        self.unlimited = max_cycles < 0


class GenerativeSystem:
    component_types = [Generative]

    def process(self, tick: int, generators):
        for generator in generators:
            value = getattr(generator.owner, generator.target_attr)
            if value >= generator.max_value:
                continue

            if not generator.unlimited:
                if generator.cycles > generator.max_cycles:
                    logger.debug(
                        'process_generator_max_reached',
                        cycles=generator.cycles,
                        max_cycles=generator.max_cycles,
                        generator=generator,
                        system=self.__class__.__name__,
                    )
                    generator.owner.components.remove(generator)
                    continue

            if generator.ticks < generator.ticks_per_cycle:
                generator.ticks += 1
                continue

            generator.cycles += 1
            generator.ticks = 0

            value += generator.increase_per_cycle

            setattr(generator.owner, generator.target_attr, value)
