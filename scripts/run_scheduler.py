import argparse
import os
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for scheduler helper script."""
    parser = argparse.ArgumentParser(description="Run APScheduler process or run-once jobs.")
    parser.add_argument(
        "--once",
        choices=["data", "strategy", "paper", "backtest", "all"],
        default=None,
        help="Run one scheduler job immediately and exit.",
    )
    return parser.parse_args()


def main() -> int:
    """Entrypoint for local scheduler execution helper."""
    args = parse_args()
    backend_path = Path(__file__).resolve().parents[1] / "backend"
    sys.path.insert(0, str(backend_path))

    from app.scheduler.runner import main as scheduler_main

    if args.once:
        os.environ["PYTHONUNBUFFERED"] = "1"
        sys.argv = [sys.argv[0], "--once", args.once]
    else:
        sys.argv = [sys.argv[0]]

    scheduler_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
