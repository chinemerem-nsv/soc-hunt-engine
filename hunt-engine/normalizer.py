import duckdb
from pathlib import Path
import logging

logger = logging.getLogger("SOC_Normalizer")

def initialize_normalized_db(db_path: Path = Path("clean.db")):
    conn = duckdb.connect(str(db_path))
    
    # Create canonical normalized tables
    conn.execute("""
        CREATE TABLE IF NOT EXISTS normalized_events (
            event_id VARCHAR,
            source VARCHAR,
            timestamp_utc TIMESTAMP,
            canonical_name VARCHAR,
            source_ip VARCHAR,
            destination_ip VARCHAR,
            action VARCHAR,
            schema_version VARCHAR
        );
    """)

    # Create identity alias resolution table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS identity_map (
            identity_id VARCHAR,
            canonical_name VARCHAR,
            alias VARCHAR
        );
    """)

    # Populate reference alias mapping from case desk data
    conn.execute("""
        INSERT INTO identity_map VALUES 
        ('id-v1-amina-ad4', 'amina-ad4', 'amina-ad4@example.invalid'),
        ('id-v1-amina-ad4', 'amina-ad4', 'EXAMPLE\\amina-ad4');
    """)

    conn.close()
    logger.info("DuckDB normalized schema and identity maps initialized successfully.")