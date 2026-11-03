# Execution boundary

Planned: async facade, per-call state, scheduling, process ownership, cancellation,
termination, errors, progress/logging and timing. No JavaScript or JVM runtime backend.
CPU-bound layout must not silently block the caller event loop while claiming async isolation.
