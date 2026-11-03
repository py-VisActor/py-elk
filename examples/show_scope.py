"""Print the current project scope without pretending to perform graph layout."""
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    ledger = json.loads((root / "docs/compatibility.json").read_text(encoding="utf-8"))
    print(json.dumps({"status": ledger["status"], "baseline": ledger["upstreamVersion"],
                      "plannedAlgorithms": len(ledger["algorithms"]),
                      "plannedOptions": len(ledger["options"]),
                      "implementedAlgorithms": 0,
                      "layoutAvailable": False}, indent=2))


if __name__ == "__main__":
    main()
