import structlog
import weakref

from settlers.engine.components import Component

logger = structlog.get_logger('engine.factory')


class PipelineInput:
    __slots__ = ['quantity', 'resource', '_storage']

    def __init__(self, quantity, resource, storage):
        self.resource = resource
        self._storage = storage
        self.quantity = quantity

    def can_consume(self):
        return self._storage.quantity() >= self.quantity

    def consume(self):
        consumed = 0
        for quantity in range(self.quantity):
            consumed_item = self._storage.pop()
            if consumed_item:
                consumed += 1

        return consumed


class PipelineOutput:
    __slots__ = ['quantity', 'storage', 'resource']

    def __init__(self, quantity, resource, storage):
        self.resource = resource
        self.storage = storage
        self.quantity = quantity


class Pipeline:
    __slots__ = [
        'inputs', 'output',
        'reserved', 'ticks_per_cycle',
        '__weakref__'
    ]

    def __init__(self, inputs, output, ticks_per_cycle):
        self.inputs = inputs
        self.output = output
        self.reserved = False
        self.ticks_per_cycle = ticks_per_cycle

    def consume_input(self):
        for input in self.inputs:
            if not input.can_consume():
                return False

        for input in self.inputs:
            input.consume()

    def build_outputs(self):
        outputs = []

        for _ in range(self.output.quantity):
            output = self.output.resource()
            added = self.output.storage.add(output)
            if added:
                outputs.append(output)
            else:
                break

        return outputs

    def is_available(self):
        if self.reserved:
            return False

        if self.output.storage.is_full():
            return False

        for input in self.inputs:
            if not input.can_consume():
                return False

        return True


class Worker(Component):
    __slots__ = [
        '_on_end_callbacks', 'pipeline', 'progress', 'state', 'workplace'
    ]

    exposed_as = 'work'
    exposed_methods = ['on_end', 'start', 'stop']

    def __init__(self, owner):
        super().__init__(owner)

        self.state = STATE_IDLE
        self.pipeline = None
        self.progress = 0
        self.workplace = None
        self._on_end_callbacks = []

    def can_work(self):
        if not self.workplace:
            return False

        workplace = self.workplace()
        if not workplace:
            return False

        return workplace.position() == self.owner.position

    def is_active(self):
        if not self.can_work():
            return False

        return self.state == STATE_ACTIVE

    def on_end(self, callback):
        self._on_end_callbacks.append(callback)

    def start(self, target):
        if self.workplace:
            raise RuntimeError('already working')

        if not target.can_add_worker():
            logger.debug(
                'start_target_rejected',
                target=target,
                owner=self.owner,
                component=self.__class__.__name__,
            )
            return False

        logger.debug(
            'start_requested',
            target=target,
            owner=self.owner,
            component=self.__class__.__name__,
        )

        self.workplace = weakref.ref(target)
        return target.add_worker(self)

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

        if self.workplace:
            workplace = self.workplace()
            if workplace:
                workplace.remove_worker(self)

            self.workplace = None

        logger.info(
            'stop',
            owner=self.owner,
            component=self.__class__.__name__,
        )

        self._on_end_callbacks = []

    def __repr__(self):
        return "<{owner}#{component} {id}".format(
            owner=self.owner,
            component=self.__class__.__name__,
            id=hex(id(self)),
        )

    @classmethod
    def target_components(cls):
        return [Factory]


STATE_IDLE = 'idle'
STATE_ACTIVE = 'active'


class Factory(Component):
    __slots__ = [
        'active', 'cycles', 'max_workers', 'pipelines', 'state', 'ticks',
        'workers'
    ]

    exposed_as = 'factory'
    exposed_methods = [
        'add_worker', 'can_add_worker', 'remote_worker', 'start', 'stop'
    ]

    def __init__(self, owner, pipelines, max_workers):
        super().__init__(owner)

        self.active = False
        self.max_workers = max_workers
        self.pipelines = pipelines
        self.state = STATE_IDLE
        self.workers = []

    def add_worker(self, worker):
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

    def can_add_worker(self):
        return len(self.workers) < self.max_workers

    def position(self):
        return self.owner.position

    def remove_worker(self, worker):
        for reference in self.workers:
            resolved_reference = reference()
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

    def start(self):
        self.active = True

    def state_change(self, new_state):
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

    def stop(self):
        self.active = False

    def __repr__(self):
        return "<{owner}#{component} {id}>".format(
            owner=self.owner,
            component=self.__class__.__name__,
            id=hex(id(self)),
        )


class FactorySystem:
    component_types = [Factory]

    def process(self, factories):
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

    def process_workers(self, factory):
        for worker_reference in factory.workers:
            worker = worker_reference()

            if not worker:
                self.workers.remove(worker_reference)
                continue

            # each worker should be on a different pipeline
            if not worker.can_work():
                logger.debug(
                    'process_worker_cannot_work',
                    worker=worker,
                    factory=factory,
                    system=self.__class__.__name__,
                )

                if worker.pipeline:
                    worker.pipeline.reserved = False
                    worker.pipeline = None

                worker.progress = 0
                continue

            if not worker.is_active():
                self.activate_pipeline_on_worker(factory, worker)
                if not worker.pipeline:
                    logger.debug(
                        'process_workers_no_available_pipeline',
                        worker=worker,
                        factory=factory,
                        system=self.__class__.__name__
                    )
                    continue

            pipeline = worker.pipeline()
            if worker.progress >= pipeline.ticks_per_cycle:

                outputs = pipeline.build_outputs()

                logger.debug(
                    'process_workers_work_completed',
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

    def activate_pipeline_on_worker(self, factory, worker):
        pipeline = self.available_pipeline_for_factory(factory)

        if not pipeline:
            return False

        pipeline.reserved = True
        pipeline.consume_input()

        worker.pipeline = weakref.ref(pipeline)
        worker.state_change(STATE_ACTIVE)

        logger.info(
            'activate_pipeline_on_worker_pipeline_activated',
            factory=factory,
            worker=worker,
            pipeline=pipeline,
            system=self.__class__.__name__,
        )

        return True

    def available_pipeline_for_factory(self, factory):
        for pipeline in factory.pipelines:
            if not pipeline.is_available():
                continue
            return pipeline
