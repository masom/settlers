#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import structlog
import path_fix # noqa

from settlers.engine.world import World
from settlers.game.ui import Manager

structlog.configure(
    processors=[
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(),
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False
)

logger = structlog.get_logger('run')

world = World()

options = {
    "with_low_pop": True,
    "with_house": True,
    "with_constructions": False,
    "with_sawmill": False,
}

m = Manager()
m.initialize(world, options)
m.start()
