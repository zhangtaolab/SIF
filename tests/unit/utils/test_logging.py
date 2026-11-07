"""Behavior tests for logging configuration and output suppression."""

import io
import logging
import sys
import warnings
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

import sif.utils.logging as logging_utils


@pytest.fixture(autouse=True)
def restore_logging_state(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Restore process-global logging, quiet, and warning state after every test."""
    noisy_names = ["sif", *logging_utils._NOISY_LOGGERS]
    original_loggers = {
        name: (
            logging.getLogger(name).level,
            list(logging.getLogger(name).handlers),
            logging.getLogger(name).propagate,
        )
        for name in noisy_names
    }
    original_disable = logging.root.manager.disable
    original_quiet = logging_utils._quiet_mode
    original_filters = list(warnings.filters)
    monkeypatch.delenv("TQDM_DISABLE", raising=False)
    monkeypatch.delenv("TRANSFORMERS_VERBOSITY", raising=False)
    monkeypatch.delenv("HF_HUB_DISABLE_PROGRESS_BARS", raising=False)
    try:
        yield
    finally:
        logging.disable(original_disable)
        logging_utils._quiet_mode = original_quiet
        for name, (level, handlers, propagate) in original_loggers.items():
            logger = logging.getLogger(name)
            logger.setLevel(level)
            logger.handlers = handlers
            logger.propagate = propagate
        warnings.filters = original_filters


class TestLoggingConfiguration:
    """Logging setup controls SIF levels, quiet state, and isolated suppression."""

    def test_get_logger_prefixes_module_name(self) -> None:
        """Every project logger lives below the sif namespace."""
        assert logging_utils.get_logger("search.bm25").name == "sif.search.bm25"

    def test_setup_info_uses_simple_format_and_nonquiet_state(self) -> None:
        """INFO uses a stream handler, simple format, and enables normal logging."""
        handler = logging.StreamHandler(io.StringIO())

        logging_utils.setup_logging("INFO", handler=handler)

        logger = logging.getLogger("sif")
        assert logger.level == logging.INFO
        assert logger.handlers == [handler]
        assert handler.formatter is not None
        assert handler.formatter._fmt == logging_utils.SIMPLE_FORMAT
        assert logger.propagate is False
        assert logging_utils.is_quiet() is False

    def test_setup_debug_uses_default_format(self) -> None:
        """DEBUG selects the detailed timestamped default format."""
        handler = logging.StreamHandler(io.StringIO())

        logging_utils.setup_logging("debug", handler=handler)

        assert logging.getLogger("sif").level == logging.DEBUG
        assert handler.formatter is not None
        assert handler.formatter._fmt == logging_utils.DEFAULT_FORMAT
        assert logging_utils.is_quiet() is False

    def test_custom_format_overrides_level_default(self) -> None:
        """An explicit format is honored without changing the configured level."""
        handler = logging.StreamHandler(io.StringIO())

        logging_utils.setup_logging("ERROR", "%(message)s", handler=handler)

        assert logging.getLogger("sif").level == logging.ERROR
        assert handler.formatter is not None
        assert handler.formatter._fmt == "%(message)s"

    def test_setup_creates_stderr_handler_and_replaces_existing_handlers(self) -> None:
        """The default handler targets stderr and setup does not accumulate handlers."""
        original_stderr = sys.stderr
        stderr = io.StringIO()
        monkeypatch_stderr = patch.object(sys, "stderr", stderr)
        stale_handler = logging.StreamHandler(io.StringIO())
        logging.getLogger("sif").handlers = [stale_handler]

        with monkeypatch_stderr:
            logging_utils.setup_logging("INFO")

        assert sys.stderr is original_stderr
        logger = logging.getLogger("sif")
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)
        assert logger.handlers[0].stream is stderr
        assert stale_handler not in logger.handlers

    def test_warning_quiet_mode_configures_environment_and_noisy_loggers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """WARNING activates quiet mode and sets only unset suppression variables."""
        monkeypatch.setenv("TQDM_DISABLE", "0")
        noisy = logging.getLogger("transformers")
        noisy.addHandler(logging.StreamHandler(io.StringIO()))
        transformers_logging = MagicMock()
        with patch.dict(sys.modules, {"transformers": MagicMock(logging=transformers_logging)}):
            logging_utils.setup_logging("WARNING")

        assert logging_utils.is_quiet() is True
        assert logging.root.manager.disable == logging.INFO
        assert noisy.level == logging.WARNING
        assert noisy.handlers == []
        assert noisy.propagate is False
        assert logging_utils.os.environ["TQDM_DISABLE"] == "0"
        assert logging_utils.os.environ["TRANSFORMERS_VERBOSITY"] == "error"
        assert logging_utils.os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] == "1"
        transformers_logging.set_verbosity_error.assert_called_once_with()

    def test_set_quiet_false_only_changes_global_state(self) -> None:
        """Disabling quiet mode does not unexpectedly change global logging thresholds."""
        logging_utils._quiet_mode = True
        original_disable = logging.root.manager.disable

        logging_utils.set_quiet(False)

        assert logging_utils.is_quiet() is False
        assert logging.root.manager.disable == original_disable

    def test_quiet_mode_tolerates_missing_transformers(self) -> None:
        """Optional transformers absence does not prevent quiet-mode setup."""
        with patch.dict(sys.modules, {"transformers": None}):
            logging_utils.set_quiet(True)

        assert logging_utils.is_quiet() is True

    def test_suppress_output_redirects_both_streams_and_restores_them(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The combined suppression context silences stdout and stderr temporarily."""
        with logging_utils.suppress_output():
            print("hidden stdout")
            print("hidden stderr", file=sys.stderr)

        print("visible stdout")
        print("visible stderr", file=sys.stderr)
        captured = capsys.readouterr()
        assert captured.out == "visible stdout\n"
        assert captured.err == "visible stderr\n"

    def test_suppress_stdout_and_stderr_are_independent(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Individual suppression contexts leave the other output stream untouched."""
        with logging_utils.suppress_stdout():
            print("hidden")
            print("kept error", file=sys.stderr)
        with logging_utils.suppress_stderr():
            print("kept output")
            print("hidden", file=sys.stderr)

        captured = capsys.readouterr()
        assert captured.out == "kept output\n"
        assert captured.err == "kept error\n"
