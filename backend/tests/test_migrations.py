import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class MigrationTests(unittest.TestCase):
    def test_existing_revisions_upgrade_fresh_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "database.db"
            env = os.environ.copy()
            env["COWRITER_DATABASE_URI"] = f"sqlite:///{database}"

            for command in ("upgrade", "check"):
                result = subprocess.run(
                    [sys.executable, "-m", "flask", "--app", "backend.app", "db", command],
                    cwd=ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            with sqlite3.connect(database) as connection:
                self.assertEqual(
                    connection.execute("SELECT version_num FROM alembic_version").fetchone()[0],
                    "52103eca120e",
                )
                self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])


if __name__ == "__main__":
    unittest.main()
