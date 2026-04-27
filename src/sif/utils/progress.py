"""Progress tracking utilities."""

from typing import Protocol

from rich.progress import BarColumn, Progress as RichProgress, SpinnerColumn, TaskID, TextColumn

from sif.utils.logging import get_logger


logger = get_logger(__name__)


class ProgressTracker(Protocol):
    """Protocol for progress tracking."""

    def start(self, description: str, total: int | None = None) -> None:
        """Start tracking progress."""
        ...

    def update(self, advance: int = 1) -> None:
        """Update progress."""
        ...

    def finish(self) -> None:
        """Finish tracking."""
        ...


class RichProgressTracker:
    """Progress tracker using Rich library."""

    def __init__(self) -> None:
        """Initialize progress tracker."""
        self._progress: RichProgress | None = None
        self._task_id: TaskID | None = None

    def start(self, description: str, total: int | None = None) -> None:
        """Start tracking progress.

        Args:
            description: Task description
            total: Total items (None for indeterminate)
        """
        self._progress = RichProgress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn() if total else None,
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%") if total else None,
        )
        self._progress.start()
        self._task_id = self._progress.add_task(description, total=total)

    def update(self, advance: int = 1) -> None:
        """Update progress.

        Args:
            advance: Number of items to advance
        """
        if self._progress and self._task_id is not None:
            self._progress.update(self._task_id, advance=advance)

    def finish(self) -> None:
        """Finish tracking."""
        if self._progress:
            self._progress.stop()
            self._progress = None
            self._task_id = None


class NullProgressTracker:
    """No-op progress tracker for silent operation."""

    def start(self, description: str, total: int | None = None) -> None:
        """Start tracking (no-op)."""
        pass

    def update(self, advance: int = 1) -> None:
        """Update progress (no-op)."""
        pass

    def finish(self) -> None:
        """Finish tracking (no-op)."""
        pass
