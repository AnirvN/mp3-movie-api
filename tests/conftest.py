
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from src.storage import MovieStorage


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a test client with a separate SQLite database."""
    test_db = tmp_path / "movies.db"
    test_storage = MovieStorage(db_path=test_db)

    monkeypatch.setattr(main, "storage", test_storage)

    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def sample_movies_bytes():
    """Read the sample movie CSV file."""
    filepath = Path("fixtures") / "sample_movies.csv"
    return filepath.read_bytes()


@pytest.fixture
def uploaded_movies(client, sample_movies_bytes):
    """Upload the sample movies for testing."""
    response = client.post(
        "/upload",
        files={
            "file": (
                "sample_movies.csv",
                sample_movies_bytes,
                "text/csv"
            )
        }
    )

    assert response.status_code == 200
    assert response.json()["rows"] == 20

    return response.json()
