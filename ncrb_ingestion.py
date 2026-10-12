import os
import re
import hashlib
import traceback
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# ============================================================
# NEYYAPUDAIPENNE
# NCRB BULK DATA INGESTION ENGINE
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

# Set NCRB_ROOT in .env to the folder containing the source CSV files.
NCRB_ROOT = os.getenv("NCRB_ROOT", r"C:\Neyyapudaipenne_dataset")

# PostgreSQL configuration comes from environment variables.
DB_CONFIG = {
    "username": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "database": os.getenv("POSTGRES_DB", "neyyapudaipenne"),
}


# ============================================================
# DATABASE CONNECTION
# ============================================================

def create_db_engine():

    url = URL.create(
        drivername="postgresql+psycopg2",
        username=DB_CONFIG["username"],
        password=DB_CONFIG["password"],
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        database=DB_CONFIG["database"],
    )

    return create_engine(
        url,
        pool_pre_ping=True,
        future=True,
    )


engine = create_db_engine()


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize_database():

    with engine.begin() as conn:

        # RAW layer
        conn.execute(
            text(
                """
                CREATE SCHEMA IF NOT EXISTS raw;
                """
            )
        )

        # CORE layer
        conn.execute(
            text(
                """
                CREATE SCHEMA IF NOT EXISTS core;
                """
            )
        )

        # ANALYTICS layer
        conn.execute(
            text(
                """
                CREATE SCHEMA IF NOT EXISTS analytics;
                """
            )
        )

        # Dataset registry
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS core.dataset_registry (

                    dataset_id BIGSERIAL PRIMARY KEY,

                    file_name TEXT NOT NULL,

                    file_path TEXT,

                    table_name TEXT,

                    file_hash TEXT,

                    row_count BIGINT DEFAULT 0,

                    column_count INTEGER DEFAULT 0,

                    year TEXT,

                    geography TEXT,

                    status TEXT,

                    error_message TEXT,

                    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    UNIQUE(file_hash)

                );
                """
            )
        )


# ============================================================
# FILE DISCOVERY
# ============================================================

def discover_csv_files(root_directory):

    csv_files = []

    for root, dirs, files in os.walk(root_directory):

        for file in files:

            if file.lower().endswith(".csv"):

                full_path = os.path.join(
                    root,
                    file
                )

                csv_files.append(
                    os.path.abspath(full_path)
                )

    return sorted(csv_files)


# ============================================================
# FILE HASH
# ============================================================

def calculate_file_hash(file_path):

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:

        while True:

            chunk = file.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


# ============================================================
# SAFE TABLE NAME
# ============================================================

def create_safe_table_name(file_path):

    filename = os.path.splitext(
        os.path.basename(file_path)
    )[0]

    filename = filename.lower()

    filename = re.sub(
        r"[^a-z0-9]+",
        "_",
        filename
    )

    filename = re.sub(
        r"_+",
        "_",
        filename
    )

    filename = filename.strip("_")

    if not filename:

        filename = "dataset"

    table_name = f"ncrb_{filename}"

    # PostgreSQL identifier safety
    table_name = table_name[:60]

    return table_name


# ============================================================
# CSV READER
# ============================================================

def read_ncrb_csv(file_path):

    encodings = [
        "utf-8",
        "utf-8-sig",
        "cp1252",
        "latin1",
    ]

    last_error = None

    for encoding in encodings:

        try:

            df = pd.read_csv(
                file_path,
                encoding=encoding,
                low_memory=False,
            )

            return df

        except Exception as error:

            last_error = error

    raise last_error


# ============================================================
# COLUMN CLEANING
# ============================================================

def clean_columns(df):

    cleaned_columns = []

    for index, column in enumerate(
        df.columns
    ):

        column = str(column)

        column = column.strip().lower()

        column = re.sub(
            r"[^a-z0-9]+",
            "_",
            column
        )

        column = re.sub(
            r"_+",
            "_",
            column
        )

        column = column.strip("_")

        if not column:

            column = f"column_{index + 1}"

        cleaned_columns.append(column)

    # Handle duplicate column names
    seen = {}

    final_columns = []

    for column in cleaned_columns:

        if column not in seen:

            seen[column] = 0

            final_columns.append(column)

        else:

            seen[column] += 1

            final_columns.append(
                f"{column}_{seen[column]}"
            )

    df.columns = final_columns

    return df


# ============================================================
# BASIC DATA CLEANING
# ============================================================

def basic_cleaning(df):

    df = clean_columns(df)

    # Convert empty strings into NULL
    df = df.replace(
        r"^\s*$",
        pd.NA,
        regex=True
    )

    return df


# ============================================================
# YEAR DETECTION
# ============================================================

def detect_year(file_path, df):

    filename = os.path.basename(
        file_path
    )

    years = re.findall(
        r"(20\d{2})",
        filename
    )

    if years:

        return years[-1]

    for column in df.columns:

        if "year" in str(column).lower():

            try:

                values = (
                    df[column]
                    .dropna()
                    .astype(str)
                )

                if not values.empty:

                    match = re.search(
                        r"(20\d{2})",
                        values.iloc[0]
                    )

                    if match:

                        return match.group(1)

            except Exception:

                pass

    return None


# ============================================================
# GEOGRAPHY DETECTION
# ============================================================

def detect_geography(df):

    columns = [
        str(column).lower()
        for column in df.columns
    ]

    if any(
        "district" in column
        for column in columns
    ):

        return "district"

    if any(
        "city" in column
        for column in columns
    ):

        return "city"

    if any(
        "state" in column
        for column in columns
    ):

        return "state"

    if any(
        "country" in column
        for column in columns
    ):

        return "country"

    return "unknown"


# ============================================================
# DUPLICATE CHECK
# ============================================================

def file_already_loaded(file_hash):

    query = text(
        """
        SELECT dataset_id
        FROM core.dataset_registry
        WHERE file_hash = :file_hash
        LIMIT 1;
        """
    )

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {
                "file_hash": file_hash
            }
        ).fetchone()

    return result is not None


# ============================================================
# DATASET REGISTRY
# ============================================================

def register_dataset(
    file_path,
    file_hash,
    table_name,
    row_count,
    column_count,
    year,
    geography,
    status,
    error_message=None,
):

    query = text(
        """
        INSERT INTO core.dataset_registry
        (
            file_name,
            file_path,
            table_name,
            file_hash,
            row_count,
            column_count,
            year,
            geography,
            status,
            error_message,
            loaded_at
        )

        VALUES
        (
            :file_name,
            :file_path,
            :table_name,
            :file_hash,
            :row_count,
            :column_count,
            :year,
            :geography,
            :status,
            :error_message,
            :loaded_at
        )

        ON CONFLICT (file_hash)
        DO UPDATE SET

            status =
                EXCLUDED.status,

            error_message =
                EXCLUDED.error_message,

            loaded_at =
                EXCLUDED.loaded_at;
        """
    )

    with engine.begin() as conn:

        conn.execute(
            query,
            {
                "file_name":
                    os.path.basename(file_path),

                "file_path":
                    file_path,

                "table_name":
                    table_name,

                "file_hash":
                    file_hash,

                "row_count":
                    row_count,

                "column_count":
                    column_count,

                "year":
                    year,

                "geography":
                    geography,

                "status":
                    status,

                "error_message":
                    error_message,

                "loaded_at":
                    datetime.now(),
            }
        )


# ============================================================
# LOAD ONE CSV
# ============================================================

def load_csv_to_postgres(file_path):

    print()
    print("=" * 70)

    print(
        f"PROCESSING: "
        f"{os.path.basename(file_path)}"
    )

    try:

        # ----------------------------------------------------
        # HASH
        # ----------------------------------------------------

        file_hash = calculate_file_hash(
            file_path
        )

        # ----------------------------------------------------
        # DUPLICATE CHECK
        # ----------------------------------------------------

        if file_already_loaded(
            file_hash
        ):

            print(
                "⏭ Already loaded — skipping."
            )

            return {
                "status": "SKIPPED",
                "file": file_path
            }

        # ----------------------------------------------------
        # READ CSV
        # ----------------------------------------------------

        df = read_ncrb_csv(
            file_path
        )

        print(
            f"Rows detected: "
            f"{len(df):,}"
        )

        print(
            f"Columns detected: "
            f"{len(df.columns)}"
        )

        # ----------------------------------------------------
        # CLEAN
        # ----------------------------------------------------

        df = basic_cleaning(
            df
        )

        # ----------------------------------------------------
        # METADATA
        # ----------------------------------------------------

        table_name = create_safe_table_name(
            file_path
        )

        year = detect_year(
            file_path,
            df
        )

        geography = detect_geography(
            df
        )

        # ----------------------------------------------------
        # LOAD INTO RAW SCHEMA
        # ----------------------------------------------------

        print(
            f"Loading → raw.{table_name}"
        )

        df.to_sql(
            name=table_name,
            con=engine,
            schema="raw",
            if_exists="replace",
            index=False,
            chunksize=5000,
            method="multi",
        )

        # ----------------------------------------------------
        # REGISTER DATASET
        # ----------------------------------------------------

        register_dataset(
            file_path=file_path,
            file_hash=file_hash,
            table_name=table_name,
            row_count=len(df),
            column_count=len(df.columns),
            year=year,
            geography=geography,
            status="SUCCESS",
        )

        print(
            "✅ Successfully loaded."
        )

        return {
            "status": "SUCCESS",
            "file": file_path,
            "table": table_name,
            "rows": len(df),
            "columns": len(df.columns),
        }

    except Exception as error:

        error_message = str(error)

        print(
            f"❌ FAILED: "
            f"{error_message}"
        )

        traceback.print_exc()

        try:

            file_hash = calculate_file_hash(
                file_path
            )

            register_dataset(
                file_path=file_path,
                file_hash=file_hash,
                table_name=create_safe_table_name(
                    file_path
                ),
                row_count=0,
                column_count=0,
                year=None,
                geography="unknown",
                status="FAILED",
                error_message=error_message,
            )

        except Exception:

            pass

        return {
            "status": "FAILED",
            "file": file_path,
            "error": error_message,
        }


# ============================================================
# BULK INGESTION
# ============================================================

def run_ingestion():

    print()
    print("=" * 70)

    print(
        "        NEYYAPUDAIPENNE NCRB INGESTION ENGINE"
    )

    print("=" * 70)

    print()

    print(
        f"NCRB ROOT: {NCRB_ROOT}"
    )

    # --------------------------------------------------------
    # CHECK DATASET DIRECTORY
    # --------------------------------------------------------

    if not os.path.exists(
        NCRB_ROOT
    ):

        print()
        print(
            "❌ NCRB dataset directory does not exist."
        )

        print()
        print(
            "Expected:"
        )

        print(
            NCRB_ROOT
        )

        return

    # --------------------------------------------------------
    # INITIALIZE DATABASE
    # --------------------------------------------------------

    print()

    print(
        "Initializing PostgreSQL..."
    )

    try:

        initialize_database()

    except Exception as error:

        print()

        print(
            "❌ PostgreSQL initialization failed."
        )

        print(
            f"Error: {error}"
        )

        print()

        print(
            "Check:"
        )

        print(
            "1. PostgreSQL service is running"
        )

        print(
            "2. Database 'neyyapudaipenne' exists"
        )

        print(
            "3. Username/password are correct"
        )

        return

    print(
        "✅ PostgreSQL initialized."
    )

    # --------------------------------------------------------
    # DISCOVER CSV FILES
    # --------------------------------------------------------

    print()

    print(
        "Scanning NCRB directory..."
    )

    csv_files = discover_csv_files(
        NCRB_ROOT
    )

    print()

    print(
        f"📁 CSV files discovered: "
        f"{len(csv_files)}"
    )

    if not csv_files:

        print()

        print(
            "❌ No CSV files found."
        )

        return

    # --------------------------------------------------------
    # LOAD ALL FILES
    # --------------------------------------------------------

    results = []

    for number, file_path in enumerate(
        csv_files,
        start=1
    ):

        print()

        print(
            f"[{number}/{len(csv_files)}]"
        )

        result = load_csv_to_postgres(
            file_path
        )

        results.append(
            result
        )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    successful = sum(
        1
        for result in results
        if result["status"] == "SUCCESS"
    )

    skipped = sum(
        1
        for result in results
        if result["status"] == "SKIPPED"
    )

    failed = sum(
        1
        for result in results
        if result["status"] == "FAILED"
    )

    # --------------------------------------------------------
    # FINAL REPORT
    # --------------------------------------------------------

    print()
    print()

    print("=" * 70)

    print(
        "                 INGESTION COMPLETE"
    )

    print("=" * 70)

    print()

    print(
        f"📁 Total files : {len(csv_files)}"
    )

    print(
        f"✅ Loaded      : {successful}"
    )

    print(
        f"⏭ Skipped      : {skipped}"
    )

    print(
        f"❌ Failed       : {failed}"
    )

    print()

    print(
        "PostgreSQL architecture:"
    )

    print()

    print(
        "  raw       → Original NCRB datasets"
    )

    print(
        "  core      → Standardized data"
    )

    print(
        "  analytics → Intelligence layer"
    )

    print()

    print(
        "Dataset registry:"
    )

    print(
        "  core.dataset_registry"
    )

    print()

    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    run_ingestion()