import asyncio
import contextlib
import itertools
import threading
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from portfolio_tracker.application.shared.errors import PortfolioTrackerError

type EmitProgress = Callable[[Any], None]
type TaskFunc[T] = Callable[[EmitProgress], T]
type AsyncTaskFunc[T] = Callable[[EmitProgress], Awaitable[T]]
type OnError = Callable[[PortfolioTrackerError], None]
type OnCanceled = Callable[[], None]
type OnProgress = Callable[[Any], None]


class _WorkerSignals(QObject):
    finished = Signal(int, object, Exception)
    progress = Signal(int, object)


class _Worker(QRunnable):
    def __init__(self, task_id: int, signals: _WorkerSignals) -> None:
        super().__init__()
        self._task_id = task_id
        self._signals = signals

    def _emit_progress(self, progress: object) -> None:
        self._signals.progress.emit(self._task_id, progress)

    def _execute(self) -> Any:
        raise NotImplementedError

    def run(self) -> None:
        try:
            result = self._execute()
        except Exception as error:  # pylint: disable=broad-exception-caught
            self._signals.finished.emit(self._task_id, None, error)
        else:
            self._signals.finished.emit(self._task_id, result, None)


class _SyncWorker(_Worker):
    def __init__(
        self, task_id: int, signals: _WorkerSignals, task_func: TaskFunc[Any]
    ) -> None:
        super().__init__(task_id, signals)
        self._task_func = task_func

    def _execute(self) -> Any:
        return self._task_func(self._emit_progress)


class _AsyncWorker(_Worker):
    def __init__(
        self,
        task_id: int,
        signals: _WorkerSignals,
        task_func: AsyncTaskFunc[Any],
        handle: TaskHandle,
    ) -> None:
        super().__init__(task_id, signals)
        self._async_task_func = task_func
        self._handle = handle

    def _execute(self) -> Any:
        if self._handle.cancel_requested:
            raise TaskCancelledError

        async def main() -> Any:
            task = asyncio.current_task()
            assert task is not None
            loop = asyncio.get_running_loop()

            def cancel_task() -> None:
                with contextlib.suppress(RuntimeError):
                    loop.call_soon_threadsafe(task.cancel)

            self._handle.bind_cancel_action(cancel_task)
            return await self._async_task_func(self._emit_progress)

        try:
            return asyncio.run(main())
        except asyncio.CancelledError:
            raise TaskCancelledError from None


@dataclass(frozen=True)
class TaskCallbacks:
    on_result: Callable[[Any], Any]
    on_error: OnError | None = None
    on_cancelled: OnCanceled | None = None
    on_progress: OnProgress | None = None


class TaskHandle:
    def __init__(self, task_id: int) -> None:
        self.task_id = task_id
        self._lock = threading.Lock()
        self._cancel_requested = False
        self._cancel_action: Callable[[], None] | None = None

    @property
    def cancel_requested(self) -> bool:
        return self._cancel_requested

    def cancel(self) -> None:
        with self._lock:
            if self._cancel_requested:
                return

            self._cancel_requested = True
            action = self._cancel_action

        if action is not None:
            action()

    def bind_cancel_action(self, action: Callable[[], None]) -> None:
        with self._lock:
            self._cancel_action = action
            cancel = self._cancel_requested

        if cancel:
            action()


class TaskCancelledError(Exception):
    pass


class TaskRunner(QObject):
    def __init__(
        self, parent: QObject | None = None, thread_pool: QThreadPool | None = None
    ) -> None:
        super().__init__(parent)
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._signals = _WorkerSignals()
        self._signals.finished.connect(self._on_finished)
        self._signals.progress.connect(self._on_progress)
        self._callbacks: dict[int, TaskCallbacks] = {}
        self._ids = itertools.count(1)

    def start[T](  # pylint: disable=redefined-outer-name
        self,
        task_func: TaskFunc[T],
        *,
        on_result: Callable[[T], Any],
        on_error: OnError | None = None,
        on_progress: OnProgress | None = None,
    ) -> None:
        task_id = next(self._ids)
        self._callbacks[task_id] = TaskCallbacks(on_result, on_error, None, on_progress)
        self._thread_pool.start(_SyncWorker(task_id, self._signals, task_func))

    def start_async[T](  # pylint: disable=redefined-outer-name
        self,
        task_func: AsyncTaskFunc[T],
        *,
        on_result: Callable[[T], Any],
        on_error: OnError | None = None,
        on_cancelled: OnCanceled | None = None,
        on_progress: OnProgress | None = None,
    ) -> TaskHandle:
        task_id = next(self._ids)
        handle = TaskHandle(task_id)
        self._callbacks[task_id] = TaskCallbacks(
            on_result, on_error, on_cancelled, on_progress
        )
        self._thread_pool.start(_AsyncWorker(task_id, self._signals, task_func, handle))
        return handle

    def _on_finished(self, task_id: int, result: Any, error: Exception | None) -> None:
        callbacks = self._callbacks.pop(task_id)
        if error is None:
            callbacks.on_result(result)

        elif isinstance(error, TaskCancelledError):
            if callbacks.on_cancelled:
                callbacks.on_cancelled()

        elif isinstance(error, PortfolioTrackerError) and callbacks.on_error:
            callbacks.on_error(error)

        else:
            raise error

    def _on_progress(self, task_id: int, progress: Any) -> None:
        callbacks = self._callbacks.get(task_id)
        if callbacks and callbacks.on_progress:
            callbacks.on_progress(progress)


# from portfolio_tracker.application.sync import SyncService, SyncCommand

# class SyncPresenter:
#     def __init__(self, runner: TaskRunner, service: SyncService) -> None:
#         self._runner = runner
#         self._service = service

#     def sync(self, user_id: str, command: SyncCommand) -> None:

#         async def sync_task(emit_progress: EmitProgress) -> None:
#             async for event in self._service.sync(user_id, command):
#                 emit_progress(event)

#         self._handle = self._runner.submit_async(
#             sync_task, on_result=self._on_sync_done, on_cancelled=self._on_sync_cancelled,
#         )

#     def _on_sync_done(self, result: Any) -> None:
#         pass

#     def _on_sync_cancelled(self) -> None:
#         pass
