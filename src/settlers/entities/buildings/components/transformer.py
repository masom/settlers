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
            consumed = self._storage.pop()
            if consumed:
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
        '_reserved', 'ticks_per_cycle'
    ]

    def __init__(self, inputs, output, ticks_per_cycle):
        self.inputs = inputs
        self.output = output
        self._reserved = False
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

    def reserve(self):
        self._reserved = True

    def unreserve(self):
        self._reserved = False


class Storage:
    __slots__ = ['capacity', '_storage']

    def __init__(self, capacity):
        self.capacity = capacity
        self._storage = []

    def add(self, item):
        if len(self._storage) < self.capacity:
            self._storage.append(item)
            return True
        return False

    def is_empty(self):
        return len(self._storage) == 0

    def is_full(self):
        return len(self._storage) == self.capacity

    def quantity(self):
        return len(self._storage)

    def pop(self):
        self._storage.pop()

    def remove(self, item):
        self._storage.remove(item)

    def __iter__(self):
        return iter(self._storage)


class WorkerProxy:
    __slots__ = [
        'cycles', 'pipeline', 'ticks', '_transformer', '_worker', '__weakref__'
    ]

    def __init__(self, transformer, worker):
        self.cycles = 0
        self.pipeline = None
        self.ticks = 0
        self._transformer = weakref.ref(transformer)
        self._worker = weakref.ref(worker)

    def is_active(self):
        transformer = self._transformer()
        worker = self._worker()
        return transformer.position() == worker.position()

    def pick_pipeline(self):
        transformer = self._transformer()
        worker = self._worker()

        previous_pipeline = self.pipeline
        pipeline = transformer.next_available_pipeline()
        self.pipeline = pipeline

        if previous_pipeline is None and pipeline is None:
            return

        print("{transformer}: {worker} starting to work on {pipeline}".format(
                transformer=transformer,
                worker=worker,
                pipeline=pipeline
            )
        )

    def work_completed(self, resource, quantity):
        worker = self._worker()
        worker.notify_of_work_completed(resource, quantity)

    def tick(self):
        transformer = self._transformer()
        worker = self._worker()

        if transformer is None or worker is None:
            self.request_unload(transformer, worker)
            return None

        if not self.is_active():
            self.cycles = 0
            self.ticks = 0
            self.pipeline = None
            return False

        if not self.pipeline:
            self.pick_pipeline()

            if self.pipeline:
                self.pipeline.consume_input()
            return False

        if self.ticks >= transformer.ticks_per_cycle_for(self.pipeline):
            self.cycles += 1
            self.ticks = 0
            return True

        self.ticks += 1
        return False


class Transformer(Component):
    __slots__ = ['_active', 'cycles', '_pipelines', 'ticks', '_workers']

    exposed_as = 'transform'
    exposed_methods = ['add_worker', 'remote_worker', 'start', 'stop']

    def __init__(self, owner, pipelines):
        super().__init__(owner)

        self._active = False
        self._workers = []
        self._pipelines = pipelines

    def add_worker(self, worker):
        self._workers.append(WorkerProxy(self, worker))

    def next_available_pipeline(self):
        for pipeline in self._pipelines:
            if not pipeline.is_available():
                continue

            pipeline.reserve()
            return pipeline

    def position(self):
        self.owner.position

    def remove_worker(self, worker):
        pass

    def start(self):
        self._active = True

    def stop(self):
        self._active = False

    def tick(self):
        if not self._active:
            return False

        if len(self._workers) == 0:
            return False

        for worker in self._workers:
            tick_completed = worker.tick()
            if tick_completed is None:
                print("{owner}#{self} worker {harvester} is dead.".format(
                        owner=self.owner,
                        self=self.__class__.__name__,
                        worker=worker,
                    )
                )
                continue

            if tick_completed:
                pipeline = worker.pipeline
                worker.pipeline = None
                outputs = pipeline.build_outputs()
                pipeline.unreserve()

                worker.work_completed(pipeline.output.resource, len(outputs))

                print(
                    "{owner}#{self} worker {worker} has completed {quantity} {output}"
                    .format(
                        output=pipeline.output.resource,
                        owner=self.owner,
                        quantity=len(outputs),
                        self=self.__class__.__name__,
                        worker=worker,
                    )
                )

        return True

    def ticks_per_cycle_for(self, pipeline):
        return pipeline.ticks_per_cycle
