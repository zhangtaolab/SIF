"""Behavior tests for Rich and no-op progress trackers."""

from rich.progress import BarColumn, SpinnerColumn, TaskID, TextColumn

from sif.utils.progress import NullProgressTracker, RichProgressTracker


class TestProgressTracker:
    """Progress trackers expose lifecycle behavior without depending on a terminal."""

    def test_rich_tracker_start_update_and_finish(self) -> None:
        """A determinate task advances by actual counts and finishes cleanly."""
        tracker = RichProgressTracker()

        tracker.start("Indexing", total=5)

        assert tracker._progress is not None
        assert tracker._task_id is not None
        task = tracker._progress.tasks[0]
        assert task.description == "Indexing"
        assert task.total == 5
        assert task.completed == 0
        columns = tracker._progress.columns
        assert any(isinstance(column, BarColumn) for column in columns)
        assert any(isinstance(column, SpinnerColumn) for column in columns)

        tracker.update()
        tracker.update(2)

        assert tracker._progress.tasks[0].completed == 3

        tracker.finish()

        assert tracker._progress is None
        assert tracker._task_id is None

    def test_rich_tracker_zero_total_omits_bar_and_percentage(self) -> None:
        """Zero total follows the indeterminate layout without Rich division errors."""
        tracker = RichProgressTracker()

        tracker.start("Discovering", total=0)

        assert tracker._progress is not None
        assert tracker._progress.tasks[0].total == 0
        assert all(not isinstance(column, BarColumn) for column in tracker._progress.columns)
        assert sum(isinstance(column, TextColumn) for column in tracker._progress.columns) == 1
        tracker.finish()

    def test_rich_tracker_none_total_supports_indeterminate_updates(self) -> None:
        """An unknown total still tracks completed units without a percentage column."""
        tracker = RichProgressTracker()

        tracker.start("Scanning")
        tracker.update(4)

        assert tracker._progress is not None
        assert tracker._progress.tasks[0].total is None
        assert tracker._progress.tasks[0].completed == 4
        tracker.finish()

    def test_rich_update_before_start_and_repeated_finish_are_noops(self) -> None:
        """Inactive lifecycle operations neither raise nor create progress state."""
        tracker = RichProgressTracker()

        tracker.update()
        tracker.finish()
        tracker.finish()

        assert tracker._progress is None
        assert tracker._task_id is None

    def test_rich_update_without_task_id_is_ignored(self) -> None:
        """A progress object without a task ID cannot accidentally advance another task."""
        tracker = RichProgressTracker()
        tracker.start("Indexing", total=1)
        progress = tracker._progress
        assert progress is not None
        tracker._task_id = None

        tracker.update()

        assert progress.tasks[0].completed == 0
        tracker._task_id = TaskID(0)
        tracker.finish()

    def test_null_tracker_accepts_full_lifecycle(self) -> None:
        """The disabled tracker is a safe no-op for every lifecycle operation."""
        tracker = NullProgressTracker()

        assert tracker.start("Indexing", total=3) is None
        assert tracker.update() is None
        assert tracker.update(3) is None
        assert tracker.finish() is None
