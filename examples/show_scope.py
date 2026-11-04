"""Print the current project scope without pretending to perform graph layout."""
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    ledger = json.loads((root / "docs/compatibility.json").read_text(encoding="utf-8"))
    lock = json.loads((root / "UPSTREAM.json").read_text(encoding="utf-8"))
    print(json.dumps({"status": ledger["status"], "baseline": ledger["upstreamVersion"],
                      "plannedAlgorithms": len(ledger["algorithms"]),
                      "plannedOptions": len(ledger["options"]),
                      "implementedAlgorithms": len(lock["python"]["implementedAlgorithms"]),
                      "experimentalAlgorithms": lock["python"].get("experimentalAlgorithms", []),
                      "layoutAvailable": lock["python"]["runtimeImplemented"],
                      "nativeHost": lock["python"].get("nativeHost", {}),
                      "limitation": "Experimental scope only; not full algorithm or release acceptance."}, indent=2))


if __name__ == "__main__":
    main()
