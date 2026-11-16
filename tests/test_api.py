
import pytest

import main
from src import MovieStorage


def test_movies_persist(client, test_storage, uploaded_movies):
    """Check that movies persist in SQLite."""

    new_storage = MovieStorage(test_storage.db_path)

    df = new_storage.get()

    assert len(df) == 20
    assert df.columns.tolist() == [
        "title", "release_year", "rating", "genre"
    ]

    
    import pandas as pd

    expected_titles = pd.read_csv("fixtures/sample_movies.csv")["title"].tolist()

    

    assert df["title"].tolist() == expected_titles

    stored_movies = new_storage.select_columns(
        ["title"], limit=100
    )

    response = client.get("/movies", params={"limit": 100})

    assert response.status_code == 200
    assert response.json()["total_rows"] == 20

    expected_ids = list(range(1, 21))

    assert [row["id"] for row in stored_movies] == expected_ids
    assert [
        row["id"] for row in response.json()["data"]
    ] == expected_ids


def test_cache_and_processing(client, uploaded_movies, processing_body):
    """Check caching and invalidation after processing."""

    response_100 = client.get("/movies", params={"limit": 100})
    assert response_100.status_code == 200
    assert main.cache.get(100) == response_100.json()

    response_1 = client.get("/movies", params={"limit": 1})
    assert response_1.status_code == 200
    assert main.cache.get(1) == response_1.json()

    repeated = client.get("/movies", params={"limit": 100})
    assert repeated.status_code == 200
    assert repeated.json() == response_100.json()

    processed = client.post(
        "/movies/process",
        json=processing_body
    )

    assert processed.status_code == 200

    report = processed.json()
    assert report["validation_rows_removed"] == 0
    assert report["cleaning_report"]["rows_before"] == 20
    assert report["cleaning_report"]["rows_after"] == 16
    assert report["cleaning_report"]["rows_removed"] == 4

    assert main.cache.get(100) is None
    assert main.cache.get(1) is None

    updated = client.get("/movies", params={"limit": 100})

    assert updated.status_code == 200

    data = updated.json()
    assert data["total_rows"] == 16
    assert len(data["data"]) == 16

    expected_titles = [
        f"Movie {chr(65 + i)}" for i in range(16)
    ]

    assert [
        row["title"] for row in data["data"]
    ] == expected_titles

    assert [
        row["id"] for row in data["data"]
    ] == list(range(1, 17))

    assert main.cache.get(100) == data


def test_cache_hit_skips_database(
    client, uploaded_movies, monkeypatch
):
    """Check that cached requests do not query SQLite."""

    first = client.get("/movies", params={"limit": 100})

    assert first.status_code == 200

    def fail_if_called(*args, **kwargs):
        pytest.fail("Database should not be queried on a cache hit")

    monkeypatch.setattr(
        main.storage, "select_columns", fail_if_called
    )

    monkeypatch.setattr(
        main.storage, "count_movies", fail_if_called
    )

    second = client.get("/movies", params={"limit": 100})

    assert second.status_code == 200
    assert second.json() == first.json()
