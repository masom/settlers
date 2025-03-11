from collections import defaultdict
import structlog
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, TypeVar

logger = structlog.get_logger("components")


class Components:
    __slots__ = ["components", "component_classes", "owner"]

    def __init__(self, owner: object):
        self.owner = owner
        self.components: List[Component] = []
        self.component_classes: Set[Type[Component]] = set()

    def initialize(self):
        parents: List[Type[object]] = [self.owner.__class__]
        parents.extend(self._find_parents(self.owner.__class__))

        for klass in parents:
            if "components" not in klass.__dict__:
                continue

            for component_definition in klass.components:  # type: ignore
                self.add(component_definition)

    def _find_parents(self, klass: type) -> List[type]:
        parents: List[type] = []

        for parent in klass.__bases__:
            if parent == object:
                break
            parents.append(parent)
            parents.extend(self._find_parents(parent))

        return parents

    def add(self, component_definition: Any) -> None:
        logger.debug(
            "add",
            owner=self.owner,
            component=component_definition,
        )

        component_instance: Optional[Component] = None

        if isinstance(component_definition, Component):
            component_instance = component_definition
        else:
            component_class: Optional[Type[Component]] = None
            arguments: Tuple = ()

            if type(component_definition) is tuple:
                component_class = component_definition[0]
                arguments = component_definition[1:]
            elif issubclass(component_definition, Component):
                component_class = component_definition
            else:
                raise RuntimeError(
                    "Invalid component declaration: {declaration}".format(
                        declaration=component_definition
                    )
                )

            if not component_class:
                raise RuntimeError(
                    "No component class found for {definition}".format(
                        definition=component_definition
                    )
                )

            component_instance = component_class(self.owner, *arguments)

        self.component_classes.add(component_instance.__class__)

        self.components.append(component_instance)

        ComponentManager.append(component_instance)

    def remove(self, component):
        self.components.remove(component)
        self.component_classes = set([c.__class__ for c in self.components])

        ComponentManager.remove(component)

        if hasattr(component, "exposed_as"):
            exposed_as = component.exposed_as
            multiple = False
            if hasattr(component, "expose_multiple"):
                multiple = getattr(component, "expose_multiple")

            if multiple:
                components = getattr(self.owner, exposed_as)
                components.remove(component)

                if not components:
                    delattr(self.owner, exposed_as)
            else:
                delattr(self.owner, exposed_as)

    def classes(self):
        return self.component_classes

    def __iter__(self):
        return iter(self.components)


class ComponentProxy:
    __slots__ = ["_alias", "_component", "_exposed_methods", "_owner", "__weakref__"]

    def __init__(self, owner, component):
        self._component = component
        self._exposed_methods = component.exposed_methods
        self._owner = owner

    """
    Reveal the actual object being proxied.

    :param type expected_type: Assert an instance of the provided type
        will be returned
    :return: The proxied component
    """

    def reveal(self, expected_type: Optional[type] = None) -> object:
        if expected_type:
            assert isinstance(
                self._component, expected_type
            ), "{component} should be {expected_type}, got {type}".format(
                component=self._component,
                expected_type=expected_type,
                type=self._component.__class__,
            )
        return self._component

    def __getattr__(self, attr: str):
        if attr in self._exposed_methods:
            return getattr(self._component, attr)
        else:
            exists = hasattr(self._component, attr)

            if exists:
                reason = "not exposed"
            else:
                reason = "not defined"

            message = "`{attr}` {reason} on component `{component}`".format(
                attr=attr, component=self._component.__class__, reason=reason
            )
            raise AttributeError(message)

    def __eq__(self, other) -> bool:
        if not other:
            return False

        return self._component == other._component

    def __hasattr__(self, attr: str) -> bool:
        return attr in self._exposed_methods

    def __repr__(self) -> str:
        return "<{klass}<{proxied}> methods={methods}>".format(
            proxied=self._component,
            klass=self.__class__.__name__,
            methods=self._exposed_methods,
        )


STATE_IDLE = "idle"


class Component:
    __slots__ = ("_on_end_callbacks", "owner", "state", "__weakref__")

    def __init__(self, owner) -> None:
        self._on_end_callbacks: List[Callable] = []
        self.owner = owner
        self.state = STATE_IDLE

    def owner_id(self) -> int:
        return id(self.owner)

    def on_end(self, callback: Callable) -> None:
        self._on_end_callbacks.append(callback)

    def state_change(self, new_state: str) -> None:
        if self.state == new_state:
            return

        logger.debug(
            "state_change",
            old_state=self.state,
            new_state=new_state,
            owner=self.owner,
            component=self.__class__.__name__,
        )

        self.state = new_state

    def stop(self, skip_idle_state=False) -> None:
        if not skip_idle_state:
            self.state_change(STATE_IDLE)

        for callback in self._on_end_callbacks:
            callback(self)

        self._on_end_callbacks = []


ComponentsType = Dict[Type[Component], List[Component]]


"""
Allows the ComponentManager to be interfaced with `[ComponentClass]` syntax.
"""


class ComponentManagerMeta(type):
    _components: ComponentsType = defaultdict(list)

    def __getitem__(self, component_class: type) -> list:
        return self._components[component_class]


class ComponentManager(metaclass=ComponentManagerMeta):
    _entities: Dict[int, List[Component]] = defaultdict(list)

    @classmethod
    def append(cls, component_instance: Component) -> None:

        owner_id = component_instance.owner_id()

        cls._entities[owner_id].append(component_instance)

        cls[component_instance.__class__].append(component_instance)

    @classmethod
    def remove(cls, component_instance: Component) -> None:
        owner_id = component_instance.owner_id()
        cls._entities[owner_id].remove(component_instance)
        cls[component_instance.__class__].remove(component_instance)

    @classmethod
    def entity(cls, identifier: int) -> Optional[List[Component]]:
        return cls._entities.get(identifier, None)

    FetchType = TypeVar("FetchType", bound=Component)

    @classmethod
    def fetch(cls, identifier: int, requested_component: Type[FetchType]) -> FetchType:
        component = cls.fetch_optional(identifier, requested_component)
        if component:
            return component
        
        import pdb; pdb.set_trace()
        raise RuntimeError("Component not found")

    @classmethod
    def fetch_optional(cls, identifier: int, requested_component: Type[FetchType]) -> Optional[FetchType]:
        components: Optional[List[Component]] = cls._entities.get(identifier)
        if not components:
            import pdb

            pdb.set_trace()
            raise RuntimeError("Entity not found")

        for component in components:
            if isinstance(component, requested_component):
                return component

    @classmethod
    def fetch_multi(
        cls, identifier: int, requested_components: List[Type[FetchType]]
    ) -> Optional[List[FetchType]]:
        components: Optional[List[Component]] = cls._entities.get(identifier)
        if not components:
            return

        request = tuple(requested_components)

        [component for component in components if isinstance(component, request)]

    @classmethod
    def entities_matching(cls, selection: List[type]) -> List[Tuple[int, List[Component]]]:
        entities: List[Tuple[int, List[Component]]] = []
        len_selection = len(selection)
        components: Dict[int, List[Component]] = defaultdict(list)

        for component_class in selection:
            for component in cls._components[component_class]:
                components[component.owner_id()].append(component)

        for entity, entity_components in components.items():
            if not len(entity_components) == len_selection:
                continue
            entities.append((entity, entity_components))
        return entities
