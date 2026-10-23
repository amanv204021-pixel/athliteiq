"""
Shared pytest setup.

The DATABASE_URL env var must be set BEFORE anything imports app.config,
because the engine is built at import time. conftest.py is imported by
pytest ahead of the test modules, which makes it the right place for this.

Note: we must never delete the sqlite file after the app has imported --
app.main runs create_all() on import and the connection pool then holds a
handle to that inode. Removing the file out from under it makes SQLite
report "attempt to write a readonly database". We drop/recreate the tables
through SQLAlchemy instead.
"""
import os
import tempfile

TEST_DB = os.path.join(tempfile.gettempdir(), "athleteiq_pytest.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="athleteiq_uploads_")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

# Start each run from a clean file, before the app imports it.
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
