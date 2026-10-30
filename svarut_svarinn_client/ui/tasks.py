"""One worker at a time; only the GUI thread touches Tk."""
from __future__ import annotations

from queue import Empty, Queue
from threading import Thread

from ..core.network import ApiError
from ..core.paths import StorageError


class BackgroundTask:
    def __init__(self, root, on_busy):
        self.root = root
        self.on_busy = on_busy
        self.busy = False
        self._queue = Queue()
        self._after = None
        self._closed = False
        root.bind('<Destroy>', self._destroyed, add='+')

    def start(self, work, done) -> bool:
        if self.busy or self._closed:
            return False
        self.busy = True
        self.on_busy(True)

        def worker():
            try:
                value = work()
                self._queue.put((True, value, done))
            except (ApiError, StorageError) as exc:
                self._queue.put((False, str(exc), done))
            except Exception:
                self._queue.put((False, 'Uventet feil under API-handlingen. Detaljer med legitimasjon er skjermet.', done))

        self._thread = Thread(target=worker, name='ks-test-call', daemon=False)
        try:
            self._thread.start()
        except RuntimeError:
            self.busy = False
            self.on_busy(False)
            raise ApiError('Kunne ikke starte API-arbeideren.') from None
        self._after = self.root.after(50, self._poll)
        return True

    def _poll(self):
        self._after = None
        if self._closed:
            return
        try:
            ok, value, done = self._queue.get_nowait()
        except Empty:
            self._after = self.root.after(50, self._poll)
            return
        self.busy = False
        self.on_busy(False)
        done(ok, value)

    def _destroyed(self, event):
        if event.widget is self.root:
            self._closed = True
            if self._after is not None:
                self.root.after_cancel(self._after)
                self._after = None
