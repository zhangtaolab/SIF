"""Shared CLI error boundary for foreseeable database failures (16.1 D-02/D-03/D-04).

One mechanism owns the ``Database(...)`` + ``init_schema()`` pair every CLI
command opens: known failure classes (``OSError`` at construction,
``sqlite3.Error``/``OSError`` at schema init) become remedy-bearing
``click.ClickException``s; unexpected exceptions propagate unchanged with the
handle closed. The boundary covers construction and schema init only — never
the command body (D-04: no catch-all).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import click

from sif.database.database import Database


def _database_remedy(index_path: str | Path, error: Exception) -> str:
    """Build the DB-open failure message: path + cause + remedy (D-03)."""
    return (
        f"Cannot open index database at {index_path}: {error}. "
        "Check file permissions and free disk space; the database file may be corrupted."
    )


def open_initialized_database_unmanaged(
    index_path: str | Path, database_cls: type[Database]
) -> Database:
    """Open and initialize a database without a context manager; caller owns close.

    The caller-supplied ``Database`` symbol is constructed — never a helper-owned
    import — so every command module's test patch seam keeps intercepting.
    ``Database.__init__`` creates the parent directory, so construction itself
    sits inside the OSError boundary. Known schema-init failures close the
    handle and translate to a remedy-bearing ClickException; any other exception
    closes the handle and re-raises unchanged (D-04). This variant exists for
    call sites whose handle escapes the opening scope (daemon ``arm()``).
    """
    try:
        db = database_cls(index_path)
    except OSError as e:
        raise click.ClickException(_database_remedy(index_path, e)) from e
    try:
        db.init_schema()
    except (sqlite3.Error, OSError) as e:
        db.close()
        raise click.ClickException(_database_remedy(index_path, e)) from e
    except BaseException:
        db.close()
        raise
    return db


@contextmanager
def open_initialized_database(
    index_path: str | Path, database_cls: type[Database]
) -> Generator[Database, None, None]:
    """Open and initialize a CLI database, translating only foreseeable failures."""
    db = open_initialized_database_unmanaged(index_path, database_cls)
    with db:
        yield db


def sqlite_vec_remedy(error: Exception) -> str:
    """Append the sqlite-vec install remedy to a searcher-construction error (D-03)."""
    return f"{error} Reinstall the extension with 'pip install sqlite-vec' and retry."
