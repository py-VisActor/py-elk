"""Original-only adjacent-edge rank lemma, independently source-reviewed G01.

This extends only E09's explicit v3 geometry policy. No candidate import,
layout execution, coordinate inference or change to the older v2 premises.
See references/e09-geometry-premise.json and ADR0008 for fixed source/guards.
"""
from e07_geometry_premise import premises as _previous_premises


def premises(request):
    """Within the guarded default domain, nonself edge ends have distinct ranks."""
    previous = _previous_premises(request)
    if previous is None:
        return None
    # The old validator already checks all endpoint identities, single-source
    # edges, defaults/strategies, numeric limits and original-only graph shape.
    distinct = set(previous["distinctRanks"])
    for edge in request["graph"].get("edges", []):
        source, target = edge["sources"][0], edge["targets"][0]
        if source != target:
            distinct.add(frozenset((source, target)))
    return {**previous, "distinctRanks": distinct}
