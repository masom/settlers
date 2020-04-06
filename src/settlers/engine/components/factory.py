import weakref

from settlers.engine.components import Component


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
        'reserved', 'ticks_per_cycle'
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
        if self._reserved:
            return False

        if self.output.storage.is_full():
            return False

        for input in self.inputs:
            if not input.can_consume():
                return False

        return True


class Worker(Component):
    __slots__ = ['_on_end_callbacks', 'state', 'workplace']

    exposed_as = 'work'
    exposed_methods = ['on_end', 'start', 'stop']

    def __init__(self, owner):
        super().__init__(owner)

        self.state = None
        self.workplace = None
        self._on_end_callbacks = []

    def on_end(self, callback):
        self._on_end_callbacks.append(callback)

    def start(self, target):
        if self.workplace:
            raise RuntimeError('already working')

        print("{owner}: Working at {target}".format(
                owner=self.owner,
                target=target
            )
        )

        self.workplace = weakref.ref(target)
        target.add_worker(self)

    def state_change(self, new_state):
        if self.state == new_state:
            return

        print(
            "{owner}#{component} state change: "
            "{old_state} -> {new_state}".format(
                owner=self.owner,
                component=self.__class__.__name__,
                old_state=self.state,
                new_state=new_state,
            )
        )
        self.state = new_state

    def stop(self):
        self.state_change(STATE_IDLE)

        for callback in self._on_end_callbacks:
            callback(self)

        self.workplace = None

    @classmethod
    def target_components(cls):
        return [Factory]


class WorkerProxy:
    __slots__ = [
        'pipeline', 'progress', 'factory', 'worker', '__weakref__'
    ]

    def __init__(self, factory, worker):
        self.pipeline = None
        self.progress = 0
        self.factory = weakref.ref(factory)
        self.worker = weakref.ref(worker)

    def is_active(self):
        factory = self.factory()
        worker = self.worker()
        return factory.position() == worker.position()

    def work_completed(self, resource, quantity):
        worker = self.worker()
        worker.notify_of_work_completed(resource, quantity)


STATE_IDLE = 'idle'
STATE_ACTIVE = 'active'


class Factory(Component):
    __slots__ = [
        'active', 'cycles', 'max_workers', 'pipelines', 'ticks', 'workers'
    ]

    exposed_as = 'factory'
    exposed_methods = ['add_worker', 'remote_worker', 'start', 'stop']

    def __init__(self, owner, pipelines, max_workers):
        super().__init__(owner)

        self.active = False
        self.max_workers = max_workers
        self.pipelines = pipelines
        self.workers = []

    def add_worker(self, worker):
        if len(self.workers) > self.max_workers:
            return False

        self.workers.append(WorkerProxy(self, worker))
        return True

    def position(self):
        self.owner.position

    def remove_worker(self, worker):
        for proxy in self.workers:
            if proxy.worker() == worker:
                self.workers.remove(proxy)
                return True
        return False

    def start(self):
        self.active = True

    def state_change(self, new_state):
        if self.state == new_state:
            return

        print(
            "{owner}#{component} state change: "
            "{old_state} -> {new_state}".format(
                owner=self.owner,
                component=self.__class__.__name__,
                old_state=self.state,
                new_state=new_state,
            )
        )
        self.state = new_state

    def stop(self):
        self.active = False


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

            self.process_workers(factory)

    def process_workers(self, factory):
        for worker in factory.workers:
            # each worker should be on a different pipeline
            if not worker.can_work():
                if worker.pipeline:
                    worker.pipeline.reserved = False
                    worker.pipeline = None

                worker.progress = 0
                continue

            if not worker.is_active():
                self.activate_pipeline_on_worker(factory, worker)
                if not worker.pipeline:
                    continue

            if worker.progress >= worker.pipeline.ticks_per_cycle:
                pipeline = worker.pipeline

                outputs = pipeline.build_outputs()
                worker.work_completed(pipeline.output.resource, len(outputs))

                print(
                    "{owner}#{component} worker {worker} has completed"
                    " {quantity} {output}".format(
                        output=pipeline.output.resource,
                        owner=self.owner,
                        quantity=len(outputs),
                        component=self.__class__.__name__,
                        worker=worker,
                    )
                )

                worker.pipeline = None
                worker.progress = 0
                pipeline.reserved = False
            else:
                worker.progress += 1

    def activate_pipeline_on_worker(self, factory, worker):
        pipeline = self.available_pipeline_for_factory(factory)

        if not pipeline:
            return False

        print("{factory}: {worker} starting to work on {pipeline}".format(
                factory=factory,
                worker=worker,
                pipeline=pipeline
            )
        )

        pipeline.reserved = True
        pipeline.consume_input()
        worker.pipeline = pipeline

        return True

    def available_pipeline_for_factory(self, factory):
        for pipeline in factory.pipelines:
            if not pipeline.is_available():
                continue
            return pipeline
