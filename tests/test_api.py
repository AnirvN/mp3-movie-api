
from src.storage import MovieStorage
import main


def test_upload_movies(client, uploaded_movies):
    """Test uploading the movie CSV."""
    assert uploaded_movies["filename"] == "sample_movies.csv"
    assert uploaded_movies["rows"] == 20
    assert uploaded_movies["columns"] == 4
    assert uploaded_movies["column_names"] == [
        "title", "release_year", "rating", "genre"
    ]


def test_get_movies(client, uploaded_movies):
    """Test retrieving movies with a limit."""
    response = client.get("/movies", params={"limit": 2})

    assert response.status_code == 200

    data = response.json()

    assert len(data["data"]) == 2
    assert data["total_rows"] == 20
    assert data["data"][0]["id"] == 1


def test_search_movies(client, uploaded_movies):
    """Test searching movies using SQL."""
    response = client.get(
        "/movies/search",
        params=[
            ("columns", "title"),
            ("columns", "rating"),
            ("min_rating", "8.5"),
            ("limit", "2")
        ]
    )

    assert response.status_code == 200

    movies = response.json()

    assert len(movies) == 2
    assert all(movie["rating"] >= 8.5 for movie in movies)
    assert movies[0]["rating"] >= movies[1]["rating"]


def test_upload_replaces_movies(
    client, uploaded_movies, sample_movies_bytes
):
    """Test that uploading again replaces existing movies."""
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

    result = client.get("/movies")

    assert result.status_code == 200
    assert result.json()["total_rows"] == 20


def test_database_persistence(client, uploaded_movies):
    """Test that movies remain in SQLite."""
    new_storage = MovieStorage(db_path=main.storage.db_path)

    assert new_storage.count_movies() == 20

    df = new_storage.get()

    assert len(df) == 20
