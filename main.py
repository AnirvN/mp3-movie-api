
import io
import logging
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile

from src import (
    HealthResponse,
    MovieStorage,
    MovieUploadInfo,
    MovieDataResponse,
    MovieProcessingReport,
    ProcessConfig,
    setup_logging,
    log_requests
)

from src.storage import MOVIE_COLUMNS

from data_pipeline import (
    create_cleaning_report,
    process_data,
    validate_dataframe
)


setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Movie API", version="1.0.0")
app.middleware("http")(log_requests)

storage = MovieStorage()


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the application status and version."""
    return {
        "status": "ok",
        "version": "1.0.0"
    }


@app.post("/upload", response_model=MovieUploadInfo)
async def upload_movies(file: UploadFile = File(...)):
    """Upload a CSV file and replace the movie collection."""

    filename = file.filename or ""
    extension = Path(filename).suffix.lower()

    if extension != ".csv":
        logger.warning("Unsupported file format: %s", extension)
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported."
        )

    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError
    ) as error:
        logger.warning("Invalid CSV: %s", error)
        raise HTTPException(
            status_code=400,
            detail="Unable to read the CSV file."
        ) from error

    if len(df.columns) != len(MOVIE_COLUMNS) or set(df.columns) != set(MOVIE_COLUMNS):
        raise HTTPException(
            status_code=400,
            detail="CSV must contain exactly: title, release_year, rating, genre."
        )

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="CSV must contain at least one movie."
        )

    df = df[MOVIE_COLUMNS]

    storage.save(df)

    logger.info(
        "Uploaded movies: filename=%s, rows=%s",
        filename,
        len(df)
    )

    return {
        "filename": filename,
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": df.columns.tolist()
    }


@app.get("/movies", response_model=MovieDataResponse)
def get_movies(limit: int = Query(default=100, ge=1)):
    """Retrieve stored movies."""

    records = storage.select_columns(MOVIE_COLUMNS, limit)
    total_rows = storage.count_movies()

    logger.info(
        "Retrieved movies: returned_rows=%s",
        len(records)
    )

    return {
        "data": records,
        "total_rows": total_rows
    }


@app.get("/movies/search", response_model=list[dict])
def query_movies(
    columns: list[str] = Query(default=["title"]),
    min_rating: float = Query(default=0, ge=0, le=10),
    limit: int = Query(default=100, ge=1)
):
    """Search movies using SQL."""

    try:
        results = storage.query_movies(
            columns,
            min_rating,
            limit
        )

    except ValueError as error:
        logger.warning("Movie search failed: %s", error)
        raise HTTPException(
            status_code=400,
            detail=str(error)
        ) from error

    logger.info(
        "Queried movies: columns=%s, min_rating=%s, returned_rows=%s",
        columns,
        min_rating,
        len(results)
    )

    return results


@app.post(
    "/movies/process",
    response_model=MovieProcessingReport
)
def process_movies(config: ProcessConfig):
    """Validate and process the stored movie collection."""

    df = storage.get()

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="No movies available to process."
        )

    config_dict = config.model_dump()
    validation = config_dict["validation"]

    for column in validation["numeric_columns"]:
        if column not in df.columns:
            raise HTTPException(
                status_code=400,
                detail=f"Numeric column not found: {column}"
            )

    try:
        validated_df = validate_dataframe(
            df,
            validation["required_columns"],
            validation["numeric_columns"]
        )

        validation_rows_removed = len(df) - len(validated_df)

        before_processing = validated_df.copy()

        processed_df = process_data(
            validated_df,
            config_dict
        )

        cleaning_report = create_cleaning_report(
            before_processing,
            processed_df
        )

    except ValueError as error:
        logger.warning("Processing failed: %s", error)
        raise HTTPException(
            status_code=400,
            detail=str(error)
        ) from error

    storage.save(processed_df)

    logger.info(
        "Processed movies: validation_removed=%s, "
        "rows_before=%s, rows_after=%s",
        validation_rows_removed,
        cleaning_report["rows_before"],
        cleaning_report["rows_after"]
    )

    return {
        "validation_rows_removed": validation_rows_removed,
        "cleaning_report": cleaning_report
    }
