import weakref

from settlers.entities.components import Component


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


class WorkerProxy:
    __slots__ = [
        'pipeline', 'progress', 'factory', 'worker', '__weakref__'
    ]

    def __init__(self, factory, worker):
        self.cycles = 0
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


class FactorySystem:
    def process(self, factories):
        for factory in factories:
            if not factory.active:
                continue

            if not factory.workers:
                continue

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


class Factory(Component):
    __slots__ = ['active', 'cycles', 'pipelines', 'ticks', 'workers']

    exposed_as = 'factory'
    exposed_methods = ['add_worker', 'remote_worker', 'start', 'stop']

    def __init__(self, owner, pipelines):
        super().__init__(owner)

        self.active = False
        self.workers = []
        self.pipelines = pipelines

    def add_worker(self, worker):
        self.workers.append(WorkerProxy(self, worker))

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

    def stop(self):
        self.active = False
