import structlog
import weakref
from typing import List, Optional, Type

from settlers.engine.components import Component
from settlers.engine.components.worker import Worker
from settlers.engine.entities.resources import Resource
from settlers.engine.entities.resources.resource_storage import ResourceStorage


STATE_IDLE = 'idle'
STATE_ACTIVE = 'active'


logger = structlog.get_logger('engine.factory')


class PipelineInput:
    __slots__ = ('quantity', 'resource', '_storage')

    def __init__(
        self, quantity: int, resource: Type[Resource], storage: ResourceStorage
    ):
        self.resource = resource
        self._storage = storage
        self.quantity = quantity

    def can_consume(self) -> bool:
        return self._storage.quantity() >= self.quantity

    def consume(self) -> int:
        consumed = 0
        for quantity in range(self.quantity):
            consumed_item: Optional[Type[Resource]] = self._storage.pop()
            if consumed_item:
                consumed += 1

        return consumed


class PipelineOutput:
    __slots__ = ('quantity', 'storage', 'resource')

    def __init__(
        self, quantity: int, resource: Type[Resource], storage: ResourceStorage
    ):
        self.resource = resource
        self.storage = storage
        self.quantity = quantity


class Pipeline:
    __slots__ = (
        'inputs', 'output',
        'reserved', 'ticks_per_cycle',
        '__weakref__'
    )

    def __init__(
        self, inputs: List[PipelineInput], output: PipelineOutput,
        ticks_per_cycle: int
    ):
        self.inputs: List[PipelineInput] = inputs
        self.output: PipelineOutput = output
        self.reserved = False
        self.ticks_per_cycle = ticks_per_cycle

    def consume_input(self) -> bool:
        for input in self.inputs:
            if not input.can_consume():
                return False

        for input in self.inputs:
            input.consume()

        return True

    def build_outputs(self) -> List[Resource]:
        outputs: List[Resource] = []

        for _ in range(self.output.quantity):
            output: Type[Resource] = self.output.resource
            added: bool = self.output.storage.add(output)
            if added:
                outputs.append(output)
            else:
                break

        return outputs

    def is_available(self) -> bool:
        if self.reserved:
            return False

        if self.output.storage.is_full():
            return False

        for input in self.inputs:
            if not input.can_consume():
                return False

        return True


class FactoryWorker(Worker):
    _target_components: List[type] = []

    @classmethod
    def target_components(cls) -> list:
        if not cls._target_components:
            cls._target_components.append(Factory)
        return cls._target_components


class Factory(Component):
    __slots__ = (
        'active', 'cycles', 'max_workers', 'pipelines', 'state', 'ticks',
        'workers'
    )

    exposed_as = 'factory'
    exposed_methods = (
        'add_worker', 'can_add_worker', 'remote_worker', 'start', 'stop'
    )

    def __init__(self, owner, pipelines: List[Pipeline], max_workers: int):
        super().__init__(owner)

        self.active: bool = False
        self.max_workers: int = max_workers
        self.pipelines: list = pipelines
        self.state: str = STATE_IDLE
        self.workers: List[weakref.ReferenceType[Worker]] = []

    def add_worker(self, worker: Worker) -> bool:
        if not self.can_add_worker():
            return False

        logger.debug(
            'add_worker',
            owner=self.owner,
            component=self.__class__.__name__,
            worker=worker,
        )

        self.workers.append(weakref.ref(worker))

        if not self.active:
            self.active = True

        return True

    def can_add_worker(self) -> bool:
        return len(self.workers) < self.max_workers

    def position(self):
        return self.owner.position

    def remove_worker(self, worker: Worker) -> bool:
        for reference in self.workers:
            resolved_reference: Optional[Worker] = reference()
            if not resolved_reference:
                self.workers.remove(reference)
                continue

            if resolved_reference == worker:
                logger.debug(
                    'remove_worker',
                    component=self.__class__.__name__,
                    worker=worker,
                )

                self.workers.remove(reference)
                return True
        return False

    def start(self) -> bool:
        if not self.workers:
            return False

        self.active = True
        return True

    def state_change(self, new_state: str) -> None:
        if self.state == new_state:
            return

        logger.debug(
            'state_change',
            owner=self.owner,
            component=self.__class__.__name__,
            old_state=self.state,
            new_state=new_state
        )

        self.state = new_state

    def stop(self) -> None:
        self.active = False

    def __repr__(self) -> str:
        return "<{owner}#{component} {id}>".format(
            owner=self.owner,
            component=self.__class__.__name__,
            id=hex(id(self)),
        )


class FactorySystem:
    component_types = [Factory]

    def __init__(self) -> None:
        self._last_checked_at: int = 0

    def should_process(self, tick: int) -> bool:
        if (tick - self._last_checked_at) < 500:
            return False
        self._last_checked_at = tick

        return True

    def process(self, tick: int, factories: List[Factory]) -> None:
        for factory in factories:
            if not factory.active:
                continue

            if not factory.workers:
                continue

            if factory.state == STATE_IDLE:
                factory.state_change(STATE_ACTIVE)
                continue

            if factory.state == STATE_ACTIVE:
                self.process_workers(factory)
                continue

    def process_workers(self, factory: Factory) -> None:
        for worker_reference in factory.workers:
            worker: Optional[Worker] = worker_reference()

            if not worker:
                factory.workers.remove(worker_reference)
                continue

            if not worker.can_work():
                if worker.pipeline:
                    worker.pipeline.reserved = False
                    worker.pipeline = None

                worker.progress = 0

                if not worker.owner.position == factory.position():
                    destination = worker.owner.travel.destination
                    if destination:
                        if destination().position == factory.position():
                            continue
                        else:
                            raise RuntimeError('we got a problem')

                    worker.owner.travel.start(factory.owner)
                continue

            if not worker.is_active():
                self.activate_pipeline_on_worker(factory, worker)

            if not worker.pipeline:
                continue

            pipeline: Pipeline = worker.pipeline

            if worker.progress >= pipeline.ticks_per_cycle:
                outputs: List[Resource] = pipeline.build_outputs()

                logger.debug(
                    'process_workers:work_completed',
                    output=pipeline.output.resource,
                    quantity=len(outputs),
                    worker=worker,
                    component=factory,
                    owner=factory.owner,
                    system=self.__class__.__name__,
                )

                worker.pipeline = None
                worker.progress = 0
                pipeline.reserved = False

                worker.state_change(STATE_IDLE)
            else:
                worker.progress += 1

    def activate_pipeline_on_worker(self, factory: Factory, worker) -> bool:
        pipeline: Optional[Pipeline] = self.available_pipeline_for_factory(
            factory
        )

        if not pipeline:
            return False

        pipeline.reserved = True
        pipeline.consume_input()

        worker.pipeline = pipeline 
        worker.state_change(STATE_ACTIVE)

        logger.info(
            'activate_pipeline_on_worker:pipeline_activated',
            factory=factory,
            worker=worker,
            pipeline=pipeline,
            system=self.__class__.__name__,
        )

        return True

    def available_pipeline_for_factory(
        self, factory: Factory
    ) -> Optional[Pipeline]:
        for pipeline in factory.pipelines:
            if not pipeline.is_available():
                continue
            return pipeline
        return None
