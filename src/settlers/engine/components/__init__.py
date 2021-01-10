from collections import defaultdict
import structlog
from typing import List

logger = structlog.get_logger('components')


class Components:
    __slots__ = ['components', 'component_classes', 'owner']

    def __init__(self, owner):
        self.owner = owner
        self.components = []
        self.component_classes = set([])

    def initialize(self):
        parents = [self.owner.__class__]
        parents.extend(self._find_parents(self.owner.__class__))

        for klass in parents:
            if 'components' not in klass.__dict__:
                continue

            for component_definition in klass.components:
                self.add(component_definition)

    def _find_parents(self, klass):
        parents = []

        for parent in klass.__bases__:
            if parent == object:
                break
            parents.append(parent)
            parents.extend(self._find_parents(parent))

        return parents

    def add(self, component_definition):
        logger.debug(
            "add",
            owner=self.owner,
            component=component_definition,
        )

        component_instance = None

        if isinstance(component_definition, Component):
            component_instance = component_definition
        else:
            component_class = None
            arguments = []

            if type(component_definition) is tuple:
                params = list(component_definition)
                component_class = params.pop(0)
                arguments = params
            elif issubclass(component_definition, Component):
                component_class = component_definition
            else:
                raise RuntimeError(
                    "Invalid component declaration: {declaration}"
                    .format(
                        declaration=component_definition
                    )
                )

            component_instance = component_class(self.owner, *arguments)

        self.component_classes.add(component_instance.__class__)

        self.components.append(component_instance)

        ComponentManager[component_instance.__class__].append(
            component_instance
        )

        if hasattr(component_instance, 'exposed_as'):
            multiple = False
            if hasattr(component_instance, 'expose_multiple'):
                multiple = getattr(component_instance, 'expose_multiple')

            exposed_as = component_instance.exposed_as
            exposed_as_defined = hasattr(self.owner, exposed_as)

            if not multiple and exposed_as_defined:
                raise RuntimeError(
                    "{owner} already defined {exposed_as}".format(
                        owner=self.owner,
                        exposed_as=exposed_as
                    )
                )

            component_proxy = ComponentProxy(self.owner, component_instance)
            setattr(self.owner, exposed_as, component_proxy)

    def remove(self, component):
        self.components.remove(component)
        self.component_classes = set([c.__class__ for c in self.components])

        ComponentManager[component.__class__].remove(component)

        if hasattr(component, 'exposed_as'):
            exposed_as = component.exposed_as
            multiple = False
            if hasattr(component, 'expose_multiple'):
                multiple = getattr(component, 'expose_multiple')

            if multiple:
                components = getattr(self.owner, exposed_as)
                components.remove(component)
            else:
                delattr(self.owner, exposed_as)

    def classes(self):
        return self.component_classes

    def __iter__(self):
        return iter(self.components)


class ComponentProxy:
    __slots__ = [
        '_alias', '_component', '_exposed_methods', '_owner',
        '__weakref__'
    ]

    def __init__(self, owner, component):
        self._component = component
        self._exposed_methods = component.exposed_methods
        self._owner = owner

    '''
    Reveal the actual object being proxied.

    :param type expected_type: Assert an instance of the provided type
        will be returned
    :return: The proxied component
    '''
    def reveal(self, expected_type=None):
        if expected_type:
            assert isinstance(self._component, expected_type), \
                "{component} should be {expected_type}, got {type}".format(
                    component=self._component,
                    expected_type=expected_type,
                    type=self._component.__class__
                )
            
        return self._component

    def __getattr__(self, attr):
        if attr in self._exposed_methods:
            return getattr(self._component, attr)
        else:
            exists = hasattr(self._component, attr)

            if exists:
                reason = 'not exposed'
            else:
                reason = 'not defined'

            message = "`{attr}` {reason} on component `{component}`".format(
                attr=attr,
                component=self._component.__class__,
                reason=reason
            )
            raise AttributeError(message)

    def __eq__(self, other):
        if not other:
            return False

        return self._component == other._component

    def __hasattr__(self, attr):
        return attr in self._exposed_methods

    def __repr__(self):
        return "<{klass}<{proxied}> methods={methods}>".format(
            proxied=self._component,
            klass=self.__class__.__name__,
            methods=self._exposed_methods,
        )


STATE_IDLE = 'idle'


class Component:
    __slots__ = ['_on_end_callbacks', 'owner', 'state', '__weakref__']

    def __init__(self, owner):
        self._on_end_callbacks = []
        self.owner = owner
        self.state = STATE_IDLE

    def on_end(self, callback):
        self._on_end_callbacks.append(callback)

    def state_change(self, new_state):
        if self.state == new_state:
            return

        logger.debug(
            'state_change',
            old_state=self.state,
            new_state=new_state,
            owner=self.owner,
            component=self.__class__.__name__,
        )

        self.state = new_state

    def stop(self):
        self.state_change(STATE_IDLE)

        for callback in self._on_end_callbacks:
            callback(self)

        self._on_end_callbacks = []


class ComponentManagerMeta(type):
    _components: dict = defaultdict(list)

    def __getitem__(self, component_class: type) -> list:
        return self._components[component_class]


class ComponentManager(metaclass=ComponentManagerMeta):
    _components: dict = defaultdict(list)

    @classmethod
    def entities_matching(self, selection: List[type]) -> list:
        entities = []
        len_selection = len(selection)
        components = defaultdict(list)

        for component_class in selection:
            for component in self._components[component_class]:
                components[component.owner].append(component)

        for entity, entity_components in components.items():
            if not len(entity_components) == len_selection:
                continue
            entities.append((entity, entity_components))
        return entities
