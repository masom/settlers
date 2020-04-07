import structlog
import path_fix # noqa

from settlers.engine.world import World
from settlers.game import setup

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
setup(world)

world.initialize()

for _ in range(50):
    logger.debug(
        'tick'
    )
    world.process()
