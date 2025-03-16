#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import structlog
import path_fix  # noqa

from settlers.engine.world import World
from settlers.game.ui import Manager
from settlers.game.setup import setup
from settlers.entities.map import Map


structlog.configure(
    processors=[
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger("run")

options = {
    "with_low_pop": True,
    "with_house": True,
    "with_constructions": True,
    "with_sawmill": True,
}


logger.info("Map init")

map = Map()
map.generate()

logger.info("World setup")
world = World(map=map)

setup(world, options)

logger.info("World init")
world.initialize()

logger.info("UI init")
m: Manager = Manager()
m.boot()
m.start(world, map)
