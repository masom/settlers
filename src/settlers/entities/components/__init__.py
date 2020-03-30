class Components:
    __slots__ = ['components', 'owner']

    def __init__(self, owner):
        self.owner = owner
        self.components = []

    def initialize(self):
        parents = [self.owner.__class__]
        parents.extend(self.owner.__class__.__bases__)

        for parent_class in parents:
            print("{parent_class}".format(parent_class=parent_class))
            if not hasattr(parent_class, 'components'):
                return

            for component_class in parent_class.components:
                self._register_component(component_class)

    def add(self, component):
        print(
            "{owner}#{self} adding {component}".format(
                owner=self.owner,
                self=self.__class__.__name__,
                component=component,
            )
        )

        self._register_component(component)

    def _register_component(self, component_definition):
        print(
            "{owner} registering {component}".format(
                owner=self.owner,
                component=component_definition,
            )
        )

        component_instance = None

        if isinstance(component_definition, Component):
            component_instance = component_definition
        else:
            component_class = None
            arguments = []

            if type(component_definition) is tuple:
                definition = list(component_definition)

                component_class = definition.pop(0)
                arguments = definition
            elif issubclass(component_definition, Component):
                component_class = component_definition
            else:
                raise

            component_instance = component_class(self.owner, *arguments)

        self.components.append(component_instance)

        if hasattr(component_instance, 'exposed_as'):
            component_proxy = ComponentProxy(self.owner, component_instance)
            setattr(self.owner, component_instance.exposed_as, component_proxy)

    def remove(self, component):
        try:
            self.components.remove(component)
        except ValueError:
            return

    def tick(self):
        for component_instance in self.components:
            if hasattr(component_instance, 'tick'):
                component_instance.tick()


class ComponentProxy:
    __slots__ = ['_alias', '_component', '_exposed_methods', '_owner']

    def __init__(self, owner, component):
        self._component = component
        self._exposed_methods = component.exposed_methods
        self._owner = owner

        print(
            "ComponentProxy on {owner} enabled for component {component}, "
            "as {alias}, and "
            "exposing {exposed_methods}".format(
                alias=component.exposed_as,
                component=component,
                exposed_methods=self._exposed_methods,
                owner=owner,
            )
        )

    def __getattr__(self, attr):
        if attr in self._exposed_methods:
            return getattr(self._component, attr)
        else:
            raise AttributeError(
                "`{attr}` not found on component `{component}`".format(
                    attr=attr,
                    component=self._component.__class__,
                )
            )

    def __hasattr__(self, attr):
        return attr in self._exposed_methods


class Component:
    def __init__(self, owner):
        self.owner = owner
