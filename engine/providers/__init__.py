"""engine.providers is a package of pluggable brokerage connectors.
Each provider module exposes one function:

    fetch_snapshot(config: dict) -> EquitySnapshot

so scripts/update_performance.py can stay provider-agnostic and swap
sources by changing config, not code.
"""
