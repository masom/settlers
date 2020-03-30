import weakref

from settlers.entities.components import Component


class WorkerProxy:
    __slots__ = ['_worker', '_target', '__weakref__']

    def __init__(self, worker, target):
        self._worker = weakref.ref(worker)
        self._target = weakref.ref(target)

    def notify_of_work_completed(self, resource, quantity):
        worker = self._worker()
        if not worker:
            return None

        print("{owner}: we completed {quantity} {resource}!".format(
                owner=worker.owner,
                quantity=quantity,
                resource=resource,
            )
        )

        return True

    def position(self):
        worker = self._worker()
        worker.owner.position

    def stop_working(self):
        target = self._target()
        if not target:
            return

        target.worker_stopped()


class Worker(Component):
    __slots__ = ['proxy']

    exposed_as = 'working'
    exposed_methods = ['work_at']

    def __init__(self, owner):
        super().__init__(owner)

        self.proxy = None

    def work_at(self, target):
        if self.proxy:
            raise

        print("{owner}: Working at {target}".format(
                owner=self.owner,
                target=target
            )
        )

        self.proxy = WorkerProxy(self, target)
        target.transform.add_worker(self.proxy)

    def stop(self):
        if not self.proxy:
            raise

        self.proxy.stop_working()
        self.proxy = None
