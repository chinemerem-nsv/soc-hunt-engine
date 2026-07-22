import pytest
from pathlib import Path
import duckdb

def test_normalized_timeline_exists():
    assert Path("normalized-timeline.csv").exists(), "Normalized timeline missing at root!"

def test_duckdb_integrity():
    conn = duckdb.connect("clean.db", read_only=True)
    count = conn.execute("SELECT COUNT(*) FROM normalized_events;").fetchone()[0]
    assert count > 700000, f"Expected >700,000 events, found {count}"
    conn.close()
