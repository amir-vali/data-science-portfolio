"""Data ingestion script for the UCI 'Diabetes 130-US hospitals for years 1999-2008' dataset.

What it does:
- Optionally downloads and unzips the dataset into data/raw/
- Cleans missing markers ('?') -> NULL
- Creates a DuckDB database in data/processed/
- Creates a few tables to enable SQL analysis:
    - encounters: one row per encounter (cleaned)
    - patients: one row per patient (basic demographics)
    - diagnoses_long: diagnoses in long format for joins/aggregations

Run from the project root (where 'data/' and 'src/' exist):
    python src/data_ingest.py --download
or, if you already have diabetic_data.csv:
    python src/data_ingest.py --csv data/raw/diabetic_data.csv
"""

from __future__ import annotations

import argparse
import sys
import zipfile
import urllib.request
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd


UCI_ZIP_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/00296/dataset_diabetes.zip"
DEFAULT_DB_PATH = Path("data/processed/readmission.duckdb")
DEFAULT_RAW_DIR = Path("data/raw")


def download_file(url: str, dest_path: Path) -> None:
    """Download a file from url to dest_path."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading: {url}")
    print(f"To:          {dest_path}")
    with urllib.request.urlopen(url) as r, open(dest_path, "wb") as f:
        f.write(r.read())


def unzip(zip_path: Path, extract_to: Path) -> None:
    """Unzip zip_path into extract_to."""
    extract_to.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_to)
    print(f"Extracted to: {extract_to}")


def resolve_csv_path(raw_dir: Path, explicit_csv: Optional[Path]) -> Path:
    """Resolve the CSV path either from explicit argument or from raw_dir contents."""
    if explicit_csv is not None:
        if not explicit_csv.exists():
            raise FileNotFoundError(f"CSV not found: {explicit_csv}")
        return explicit_csv

    # Common expected location after unzipping (some zips extract into a subfolder)
    candidate = raw_dir / "diabetic_data.csv"
    if candidate.exists():
        return candidate

    # Search recursively for the expected filename first
    recursive_expected = list(raw_dir.rglob("diabetic_data.csv"))
    if recursive_expected:
        return recursive_expected[0]

    # Fallback: search for any CSV recursively
    csvs = list(raw_dir.rglob("*.csv"))
    if not csvs:
        raise FileNotFoundError(
            "No CSV found in data/raw/. Provide --csv or run with --download."
        )
    return csvs[0]


def prepare_dataframe(csv_path: Path) -> pd.DataFrame:
    """Load CSV and apply minimal cleaning and target feature creation."""
    df = pd.read_csv(csv_path)

    # Standardize missing markers
    df = df.replace("?", pd.NA)

    # Create target columns
    if "readmitted" not in df.columns:
        raise ValueError("Expected column 'readmitted' not found in dataset.")

    df["readmission_30d"] = (df["readmitted"] == "<30").astype("int8")
    df["readmission_any"] = (df["readmitted"] != "NO").astype("int8")

    # Basic sanity: ensure IDs exist
    for col in ("encounter_id", "patient_nbr"):
        if col not in df.columns:
            raise ValueError(f"Expected column '{col}' not found in dataset.")

    return df


def write_duckdb(df: pd.DataFrame, db_path: Path, encounters_table: str = "encounters") -> None:
    """Write cleaned data into DuckDB tables."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path))
    try:
        # Overwrite tables to keep the pipeline repeatable
        con.execute(f"DROP TABLE IF EXISTS {encounters_table}")
        con.execute("DROP TABLE IF EXISTS patients")
        con.execute("DROP TABLE IF EXISTS diagnoses_long")

        con.register("df", df)

        # Main encounter table (one row per hospital encounter)
        con.execute(
            f"""
            CREATE TABLE {encounters_table} AS
            SELECT * FROM df
            """
        )

        # Patient-level table (basic demographics; extend later if needed)
        demographic_cols = [c for c in ["patient_nbr", "race", "gender", "age"] if c in df.columns]
        if demographic_cols:
            con.execute(
                f"""
                CREATE TABLE patients AS
                SELECT DISTINCT {", ".join(demographic_cols)}
                FROM {encounters_table}
                """
            )

        # Diagnoses long table for SQL joins (diag_1/2/3)
        diag_cols = [c for c in ["diag_1", "diag_2", "diag_3"] if c in df.columns]
        if diag_cols:
            unions = []
            for i, c in enumerate(diag_cols, start=1):
                unions.append(
                    f"""
                    SELECT
                        encounter_id,
                        patient_nbr,
                        {i} AS diag_position,
                        {c} AS diag_code
                    FROM {encounters_table}
                    WHERE {c} IS NOT NULL
                    """
                )
            union_sql = "\nUNION ALL\n".join(unions)
            con.execute(
                f"""
                CREATE TABLE diagnoses_long AS
                {union_sql}
                """
            )

        # Store a lightweight view for convenience
        con.execute("DROP VIEW IF EXISTS v_encounters_min")
        cols_min = [c for c in [
            "encounter_id", "patient_nbr", "race", "gender", "age",
            "time_in_hospital", "num_lab_procedures", "num_procedures",
            "num_medications", "number_diagnoses", "readmitted",
            "readmission_30d", "readmission_any"
        ] if c in df.columns]
        con.execute(
            f"""
            CREATE VIEW v_encounters_min AS
            SELECT {", ".join(cols_min)}
            FROM {encounters_table}
            """
        )

        n = con.execute(f"SELECT COUNT(*) FROM {encounters_table}").fetchone()[0]
        pos = con.execute(f"SELECT SUM(readmission_30d) FROM {encounters_table}").fetchone()[0]
        print(f"Created DuckDB: {db_path}")
        print(f"Table '{encounters_table}': {n:,} rows")
        print(f"Readmission <30d positives: {int(pos):,} ({(pos / n * 100):.2f}%)")

    finally:
        con.close()


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest UCI diabetes readmission dataset into DuckDB.")
    p.add_argument("--download", action="store_true", help="Download and unzip the dataset into data/raw/")
    p.add_argument("--url", type=str, default=UCI_ZIP_URL, help="Dataset ZIP URL (default: UCI)")
    p.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR, help="Raw data directory (default: data/raw)")
    p.add_argument("--csv", type=Path, default=None, help="Path to diabetic_data.csv (if already downloaded)")
    p.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH, help="DuckDB output path (default: data/processed/readmission.duckdb)")
    p.add_argument("--table", type=str, default="encounters", help="Encounters table name (default: encounters)")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if args.download:
        zip_path = args.raw_dir / "dataset_diabetes.zip"
        download_file(args.url, zip_path)
        unzip(zip_path, args.raw_dir)

    csv_path = resolve_csv_path(args.raw_dir, args.csv)
    print(f"Using CSV: {csv_path}")

    df = prepare_dataframe(csv_path)
    write_duckdb(df, args.db_path, encounters_table=args.table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
