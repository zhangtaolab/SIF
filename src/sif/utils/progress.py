"""Progress tracking utilities."""

from typing import Protocol

from rich import get_console
from rich.console import Console
from rich.progress import BarColumn, Progress as RichProgress, SpinnerColumn, TaskID, TextColumn

from sif.utils.logging import get_logger


logger = get_logger(__name__)

# First frame of Rich's default "dots" spinner; used only as an encoding probe.
_SPINNER_PROBE_FRAME = "⠋"
_BRAILLE_SPINNER = "dots"
_ASCII_SPINNER = "line"


def spinner_name(console: Console | None = None) -> str:
    """Return a Rich spinner whose frames the console's stream can encode.

    Rich's default "dots" spinner renders braille frames. On a legacy Windows
    console whose output is redirected to a non-UTF-8 code page (for example
    GBK), writing the final live frame raises ``UnicodeEncodeError`` and turns
    an otherwise successful command into a raw traceback. The "line" spinner
    is pure ASCII, so it degrades honestly on any ASCII-compatible code page
    (ENG-02).
    """
    stream = (console or get_console()).file
    encoding = getattr(stream, "encoding", None)
    if not encoding:
        return _BRAILLE_SPINNER
    try:
        _SPINNER_PROBE_FRAME.encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return _ASCII_SPINNER
    return _BRAILLE_SPINNER


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
        columns = [
            SpinnerColumn(spinner_name()),
            TextColumn("[progress.description]{task.description}"),
        ]
        if total:
            columns.extend(
                [BarColumn(), TextColumn("[progress.percentage]{task.percentage:>3.0f}%")]
            )
        self._progress = RichProgress(*columns)
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
