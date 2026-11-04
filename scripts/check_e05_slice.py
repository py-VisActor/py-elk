"""Verify the actual installed E05 wheel after the expanded source gate closes."""
from check_e04_slice import main


if __name__ == "__main__":
    raise SystemExit(main(iteration="E05", builder="scripts/build_e05_suite.py",
                         source_approval="scripts/validate_e05_source_bindings.py"))
