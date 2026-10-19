import argparse
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "api"))

def main() -> None:
    from app.agent.tools.retriever import get_retriever

    parser = argparse.ArgumentParser(
        description="Index the configured local PDF report corpus and embedded charts."
    )
    parser.add_argument(
        "--force-reload",
        action="store_true",
        help="Replace the existing report collection after source PDFs are parsed.",
    )
    args = parser.parse_args()

    indexed_chunks = get_retriever().ingest_reports(force_reload=args.force_reload)
    print(f"Report corpus indexed successfully: {indexed_chunks} chunks.")


if __name__ == "__main__":
    main()
