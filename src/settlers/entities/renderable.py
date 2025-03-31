from typing import Dict, List, Optional, Tuple
import sdl2
import structlog

from sdl2.ext.sprite import Sprite

from settlers.engine.components import Component
from settlers.engine.entities.entity import Entity

logger = structlog.get_logger("engine.renderable")

RGBA = Tuple[int, int, int, int]

LabelData = Tuple[sdl2.SDL_Texture, sdl2.SDL_Rect]

LABEL_TYPE_ID = "id"
LABEL_TYPE_TASK = "task"
LABEL_TYPE_NAME = "name"
LABEL_TYPE_TEAM = "team"

LABEL_TYPES = [LABEL_TYPE_ID, LABEL_TYPE_TASK, LABEL_TYPE_NAME, LABEL_TYPE_TEAM]

LABEL_COLOR_TASK: RGBA = (255, 255, 255, 255)
LABEL_COLOR_NAME: RGBA = (100, 100, 255, 255)

LABEL_POSITION_BOTTOM = "bottom"
LABEL_POSITION_TOP = "top"


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
        "type_id",
        "_texture",
        "_rect",
    )

    def __init__(
        self,
        type_id: str,
        text: str,
        color: RGBA,
        background: Optional[RGBA] = None,
        border: Optional[RGBA] = None,
        position: str = LABEL_POSITION_BOTTOM,
        shadow: bool = False,
    ) -> None:
        self.id: int = 0
        self.type_id: str = type_id
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


def generate_label_id(
    type_id, text, color, background, border, position, shadow
) -> int:
    return fnv1a_64(
        f"{type_id}-{text}-{color}-{background}-{border}-{position}-{shadow}"
    )


class RenderableLabelCache:
    __slots__ = "labels"

    def __init__(self) -> None:
        self.labels: Dict[str, Label] = {}

    def get(
        self,
        type_id: str,
        text: str,
        color: RGBA,
        background: Optional[RGBA] = None,
        border: Optional[RGBA] = None,
        position: str = LABEL_POSITION_BOTTOM,
        shadow: bool = False,
    ) -> Label:
        key = generate_label_id(
            type_id, text, color, background, border, position, shadow
        )

        label = self.labels.get(key, None)
        if not label:
            label = Label(type_id, text, color, background, border, position, shadow)
            label.id = key
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
    __slots__ = ("rect", "labels", "type", "z")

    def __init__(self, owner: Entity, type: str, z: int = 1) -> None:
        super().__init__(owner)

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

        self.labels = {}
        self.type = new_type

    def __repr__(self) -> str:
        return "<{owner}#{component} {id}>".format(
            owner=self.owner, component=self.__class__.__name__, id=hex(id(self))
        )
