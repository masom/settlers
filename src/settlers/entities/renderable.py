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

LABEL_COLOR_TASK: RGBA = (255, 255, 255, 255)
LABEL_COLOR_NAME: RGBA = (200, 200, 255, 255)

LABEL_POSITION_BOTTOM = "bottom"


class Label:
    __slots__ = (
        "id",
        "background",
        "border",
        "color",
        "position",
        "rect",
        "shadow",
        "text",
        "_texture",
        "_rect",
    )

    def __init__(
        self,
        id: str,
        text: str,
        color: RGBA,
        background: Optional[RGBA] = None,
        border: Optional[RGBA] = None,
        position: str = LABEL_POSITION_BOTTOM,
        shadow: bool = False,
    ) -> None:
        self.id: str = id
        self.background: Optional[sdl2.SDL_Color]

        r: int
        g: int
        b: int
        a: int

        if background:
            (r, g, b, a) = background
            self.background = sdl2.SDL_Color(r, g, b, a)
        else:
            self.background = None

        self.border: Optional[sdl2.SDL_Color]

        if border:
            import pdb

            pdb.set_trace()
            (r, g, b, a) = border
            self.border = sdl2.SDL_Color(r, g, b, a)
        else:
            self.border = None

        (r, g, b, a) = color
        self.color: sdl2.SDL_Color = sdl2.SDL_Color(r, g, b, a)
        self.text: str = text
        self.position: str = position
        self.shadow = shadow


class RenderableLabelCache:
    __slots__ = "labels"

    def __init__(self) -> None:
        self.labels: Dict[str, Label] = {}

    def get(
        self,
        id: str,
        text: str,
        color: RGBA,
        background: Optional[RGBA] = None,
        border: Optional[RGBA] = None,
        position: str = LABEL_POSITION_BOTTOM,
        shadow: bool = False,
    ) -> Label:
        key = fnv1a_64(f"{id}-{text}-{color}-{background}-{border}-{position}-{shadow}")

        logger.debug(key)

        label = self.labels.get(key, None)
        if not label:
            label = Label(id, text, color, background, border, position, shadow)
            self.labels[key] = label

        return label

    def reset(self) -> None:
        self.labels: Dict[str, Label] = {}


FNV_32_PRIME = 0x01000193
FNV_64_PRIME = 0x100000001B3

FNV0_32_INIT = 0
FNV0_64_INIT = 0
FNV1_32_INIT = 0x811C9DC5
FNV1_32A_INIT = FNV1_32_INIT
FNV1_64_INIT = 0xCBF29CE484222325
FNV1_64A_INIT = FNV1_64_INIT


def fnv1a_64(data, hval_init=FNV1_64A_INIT, fnv_prime=FNV_32_PRIME, fnv_size=2**64):
    encoded_data = data.lower().encode("utf-8")

    hval = hval_init
    for byte in encoded_data:
        hval = hval ^ byte
        hval = (hval * fnv_prime) % fnv_size
    return hval


label_cache = RenderableLabelCache()


class Renderable(Component):
    __slots__ = ("rect", "labels", "sprite", "sprites", "type", "z")

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
        del self.labels[id]

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
