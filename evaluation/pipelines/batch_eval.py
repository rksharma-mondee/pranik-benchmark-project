"""Batch evaluation entrypoint."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run benchmark evaluation batches.")
    parser.add_argument("--config", required=True, type=Path, help="Path to app config YAML.")
    args = parser.parse_args()

    config = load_config(args.config)
    output_dir = Path(config["evaluation"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Loaded config for {config['app']['environment']}; reports will be written to {output_dir}")


if __name__ == "__main__":
    main()

