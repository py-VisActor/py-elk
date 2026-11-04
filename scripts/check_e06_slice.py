"""Actual E06 installed-wheel/same-suite reference execution with isolated Python."""
from check_e04_slice import main

if __name__ == "__main__":
    raise SystemExit(main(iteration="E06", builder="scripts/build_e06_suite.py",
                         source_approval="scripts/validate_e06_source_bindings.py"))
