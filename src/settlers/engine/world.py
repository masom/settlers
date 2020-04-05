class World:
    __slots__ = ['entities', 'systems']

    def __init__(self):
        self.entities = []
        self.systems = []

    def add_system(self, system):
        self.systems.append(system)

    def add_entity(self, entity):
        self.entities.append(entity)

    def initialize(self):
        for entity in self.entities:
            entity.initialize()

    def process(self):
        for system in self.systems:
            components = self.components_matching(system.component_types)

            if not components:
                continue

            system.process(components)

    def components_matching(self, wants):
        components = []

        for entity in self.entities:
            classes = set([
                component.__class__ for component in entity.components
            ])

            if classes.issuperset(wants):
                entity_components = [
                    component
                    for component in entity.components
                    if component.__class__ in wants
                ]

                components.extend(entity_components)

        return components
