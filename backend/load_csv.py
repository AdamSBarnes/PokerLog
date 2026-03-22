import argparse
from pathlib import Path

from suitedpockets.data import load_games_from_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Load game results from a CSV into SQLite.")
    parser.add_argument("csv_path", type=Path, help="Path to the CSV file.")
    parser.add_argument("--append", action="store_true", help="Append rows instead of replacing the table.")
    args = parser.parse_args()

    count = load_games_from_csv(args.csv_path, replace=not args.append)
    print(f"Loaded {count} rows into SQLite.")


if __name__ == "__main__":
    main()
