"""Run the same E07 suite against official JS and a real isolated installed wheel."""
from check_e04_slice import main

if __name__ == "__main__":
    raise SystemExit(main(iteration="E07", builder="scripts/build_e07_suite.py",
                         source_approval="scripts/validate_e07_source_bindings.py"))
