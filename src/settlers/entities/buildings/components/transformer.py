import weakref

from settlers.entities.components import Component


class PipelineInput:
    __slots__ = ['resource', 'storage']

    def __init__(self, resource, storage):
        self.resource = resource
        self.storage = storage


class Pipeline:
    __slots__ = [
        'inputs', 'output', 'output_storage',
        '_reserved', 'ticks_per_cycle'
    ]

    def __init__(self, inputs, output, output_storage, ticks_per_cycle):
        self.inputs = inputs
        self.output = output
        self.output_storage = output_storage
        self._reserved = False
        self.ticks_per_cycle = ticks_per_cycle

    def build_output(self):
        return self.output_storage.add(self.output())

    def is_available(self):
        if self._reserved:
            return False

        if self.output_storage.is_full():
            return False
        return True

    def reserve(self):
        self._reserved = True

    def unreserve(self):
        self._reserved = False


class Storage:
    __slots__ = ['capacity', 'storage']

    def __init__(self, capacity):
        self.capacity = capacity
        self.storage = []

    def add(self, item):
        if len(self.storage) < self.capacity:
            self.storage.append(item)
            return True
        return False

    def is_full(self):
        return len(self.storage) == self.capacity

    def remove(self):
        self.storage.pop()


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

        pipeline = transformer.next_available_pipeline()
        print("{transformer}: {worker} starting to work on {pipeline}".format(
                transformer=transformer,
                worker=worker,
                pipeline=pipeline
            )
        )
        self.pipeline = pipeline

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
            if pipeline.is_available():
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
                next

            if tick_completed:
                pipeline = worker.pipeline
                pipeline.unreserve()
                worker.pipeline = None
                print(
                    "{owner}#{self} worker {worker} has completed {output}"
                    .format(
                        owner=self.owner,
                        self=self.__class__.__name__,
                        worker=worker,
                        output=pipeline.output,
                    )
                )

                pipeline.build_output()
            
        return True

    def ticks_per_cycle_for(self, pipeline):
        return pipeline.ticks_per_cycle
