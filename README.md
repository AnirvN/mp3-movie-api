This FastAPI application allows the user to upload, store, search, and process movie data. The application uses SQLite to save movies permenantly and it also uses SQL queries to retrieve and filter/process them. The data processing validates movie information by cleaning and handling all values. The application uses Fakeredis to cache movie retrieval results for 90 seconds, this made repeated requests faster. The cache clears when movies are uploaded or processed so outdated data is not returned. The application also includes request logging, error handling, and automated tests to verify the database.

Running the API:

1. Activate the virtual environment:

`source venv/bin/activate`

2. Start the API:

`python -m uvicorn main:app --reload`

Open http://127.0.0.1:8000/docs

Running Tests:

`python -m pytest tests -v`


Example Processing Request:

go to: POST /movies/process


Fill this in
Request Body:


{
  "validation": {
    "required_columns": ["title", "release_year", "rating", "genre"],
    "numeric_columns": ["release_year", "rating"]
  },
  "processing": {
    "remove_duplicates": true,
    "missing": {
      "enabled": true,
      "axis": "rows"
    },
    "outliers": {
      "enabled": true,
      "columns": ["rating"],
      "method": "iqr",
      "threshold": 1.5
    }
  }
}


Expected result for sample_movies.csv:


{
  "validation_rows_removed": 0,
  "cleaning_report": {
    "rows_before": 20,
    "rows_after": 16,
    "rows_removed": 4,
    "columns_before": 4,
    "columns_after": 4,
    "columns_removed": 0
  }
}

