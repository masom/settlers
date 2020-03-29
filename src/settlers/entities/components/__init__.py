class Components:
    __slots__ = ['owner']

    def __init__(self, owner):
        self.owner = owner
        self.components = []

    def initialize(self):
        parents = self.owner.__class___.__bases__
        for parent_class in parents:
            if not hasattr(parent_class, 'components'):
                return

            for component_class in parent_class.components:
                component_instance = component_class(self)
                self.components.add(component_instance)

    def add(self, component):
        self.components.push(component)
        if hasattr(component, 'exposed_as'):
            component_proxy = ComponentProxy(component)
            setattr(self, component.exposed_as, component_proxy)

    def remove(self, component):
        try:
            self.components.remove(component)
        except ValueError:
            return

    def tick(self):
        for component_instance in self.components:
            if hasattr(component_instance, 'tick'):
                if component_instance.should_tick:
                    component_instance.tick()


class ComponentProxy:
    __slots__ = ['component', 'exposed_methods', 'owner']

    def __init__(self, owner, component):
        self._owner = owner
        self._component = component
        self._exposed_methods = component.exposed_methods

    def __getattr__(self, attr):
        if attr in self._exposed_methods:
            getattr(self._component, attr)
        else:
            raise

    def __hasattr__(self, attr):
        return attr in self._exposed_methods


class Component:
    def __init__(self, owner):
        self.owner = owner
