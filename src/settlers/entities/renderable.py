from typing import Dict, List, Optional, Tuple 
import sdl2
import structlog

from sdl2.ext.sprite import Sprite 

from settlers.engine.components import Component
from settlers.engine.entities.entity import Entity

logger = structlog.get_logger("engine.renderable")

RGBA = Tuple[int, int, int, int]

LabelData = Tuple[sdl2.SDL_Texture, sdl2.SDL_Rect]

LABEL_ID = "id"
LABEL_TASK = "task"
LABEL_NAME = "name"
LABEL_TEAM = "team"

LABELS = [LABEL_ID, LABEL_TASK, LABEL_NAME, LABEL_TEAM]

LABEL_COLOR_TASK: RGBA = (200, 200, 200, 255)
LABEL_COLOR_NAME: RGBA = (255, 200, 200, 255)

class Label:
    __slots__ = ("id", "background", "border", "color", "position", "rect", "shadow", "text", "_texture", "_rect")

    def __init__(self, id: str, text: str, color: RGBA, background: Optional[RGBA]=None, border: Optional[RGBA]=None, position: str = "bottom", shadow: bool = False) -> None:
        self.id: str = id
        self.background: Optional[sdl2.SDL_Color]

        r: int
        g: int
        b: int
        a: int

        if background:
            (r, g, b, a) = background
            self.background =  sdl2.SDL_Color(r, g, b, a)
        else:
            self.background = None

        self.border: Optional[sdl2.SDL_Color]

        if border:
            import pdb; pdb.set_trace()
            (r, g, b, a) = border 
            self.border =  sdl2.SDL_Color(r, g, b, a)
        else:
            self.border = None

        (r, g, b, a) = color
        self.color: sdl2.SDL_Color = sdl2.SDL_Color(r, g, b, a)
        self.text: str = text
        self.position: str = position
        self.shadow = shadow


class RenderableLabelCache:
    __slots__ = ("labels")

    def __init__(self) -> None:
        self.labels: Dict[str, Label] = {}

    def get(self, id: str, text: str, color: RGBA, background: Optional[RGBA]=None, border: Optional[RGBA]=None, position: str = "bottom", shadow: bool = False) -> Label:
        key = f"{id}-{text}-{color}-{background}-{border}-{position}-{shadow}"

        logger.debug(key)

        label = self.labels.get(key, None)
        if not label:
            label = Label(
                id, text, color, background, border, position, shadow
            )
            self.labels[key] = label

        return label

    def reset(self) -> None:
        self.labels: Dict[str, Label] = {}

label_cache = RenderableLabelCache()

class Renderable(Component):
    __slots__ = ("rect", "labels", "sprite", "type", "z")

    def __init__(self, owner: Entity, type: str, z: int = 1) -> None:
        super().__init__(owner)

        self.sprite: Optional[Sprite] = None

        self.type: str = type
        self.z: int = z

        self.labels: Dict[str, Label] = {}
        
    def add_label(self, label: Label) -> None:
        self.labels[label.id] = label 

    def remove_label(self, id: str) -> None:
        self.labels[id] = None
        del(self.labels[id])

    def reset(self, new_type: str) -> None:
        logger.debug(
            "reset_sprite",
            owner=self.owner,
        )

        self.sprite = None
        self.base = None
        self.labels = {}
        self.type = new_type

    def __repr__(self) -> str:
        return "<{owner}#{component} {id}>".format(
            owner=self.owner, component=self.__class__.__name__, id=hex(id(self))
        )
