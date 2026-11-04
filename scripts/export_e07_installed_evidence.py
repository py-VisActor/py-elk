"""Export E07 receipt only after recomputing a successful actual installed run."""
from export_e05_installed_evidence import main

if __name__ == "__main__":
    main(iteration="E07")
