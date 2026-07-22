import json
from pathlib import Path
import logging
import duckdb
import csv

logger = logging.getLogger("SOC_ProjectPipeline")

def clean_val(val):
    """Sanitize extracted values, stripping whitespace and null artifacts."""
    if val is None:
        return ""
    val_str = str(val).strip()
    if val_str.lower() in ["none", "null", "nil", "n/a", "undefined", ""]:
        return ""
    return val_str

def run_correlation(db_path: Path = Path("clean.db")):
    conn = duckdb.connect(str(db_path))
    logger.info("Running pipeline strictly adhering to project quarantine specifications...")

    # Drop existing table and recreate master schema
    conn.execute("DROP TABLE IF EXISTS normalized_events;")
    conn.execute("""
        CREATE TABLE normalized_events (
            source VARCHAR,
            timestamp_utc TIMESTAMP,
            canonical_name VARCHAR,
            source_ip VARCHAR,
            destination_ip VARCHAR,
            action VARCHAR,
            schema_version VARCHAR
        );
    """)

    evidence_dir = Path("evidence")
    quarantine_dir = Path("quarantine")
    quarantine_dir.mkdir(exist_ok=True)
    
    sources = ['auth', 'web', 'dns', 'firewall', 'endpoint']
    temp_csv = evidence_dir / "streaming_normalized.csv"
    quarantine_csv = quarantine_dir / "quarantine_log.csv"

    total_processed = 0
    total_quarantined = 0

    # Initialize quarantine log with required audit columns
    with open(quarantine_csv, "w", encoding="utf-8", newline="") as q_f:
        q_writer = csv.writer(q_f)
        q_writer.writerow(["source", "line_number", "reason", "raw"])

        with open(temp_csv, "w", encoding="utf-8", newline="") as out_f:
            writer = csv.writer(out_f)
            writer.writerow(["source", "timestamp", "canonical", "src_ip", "dst_ip", "action", "schema"])

            for source in sources:
                file_path = evidence_dir / f"{source}.jsonl"
                if not file_path.exists():
                    logger.warning(f"Evidence file not found: {file_path}")
                    continue

                logger.info(f"Processing and validating source: {source}...")
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, start=1):
                        line_str = line.strip()
                        if not line_str:
                            continue
                        
                        total_processed += 1
                        
                        try:
                            data = json.loads(line_str)
                        except json.JSONDecodeError:
                            total_quarantined += 1
                            q_writer.writerow([source, line_num, "json_decode_error", line_str])
                            continue

                        # Enforce schema version check
                        schema_ver = clean_val(data.get("schema_version"))
                        if not schema_ver:
                            total_quarantined += 1
                            q_writer.writerow([source, line_num, "missing_schema_version", line_str])
                            continue

                        # Enforce timestamp check
                        ts = clean_val(
                            data.get("timestamp") or 
                            data.get("event_time") or 
                            data.get("time") or 
                            data.get("datetime")
                        )
                        if not ts:
                            total_quarantined += 1
                            q_writer.writerow([source, line_num, "missing_time_field", line_str])
                            continue

                        canonical = clean_val(
                            data.get("username") or 
                            data.get("identity") or 
                            data.get("query") or 
                            data.get("rule_name") or 
                            data.get("user_agent") or 
                            data.get("user") or 
                            data.get("asset_id")
                        )
                        
                        src_ip = clean_val(
                            data.get("source_ip") or 
                            data.get("client_ip") or 
                            data.get("src_ip") or 
                            data.get("host_ip")
                        )
                        
                        dst_ip = clean_val(
                            data.get("destination_ip") or 
                            data.get("resolved_ip") or 
                            data.get("dst_ip")
                        )
                        
                        action = clean_val(
                            data.get("action") or 
                            data.get("request_method") or 
                            data.get("record_type") or 
                            data.get("process_name") or 
                            data.get("result")
                        )

                        writer.writerow([source, ts, canonical, src_ip, dst_ip, action, schema_ver])

    logger.info(f"Processed {total_processed:,} lines. Quarantined {total_quarantined:,} records to {quarantine_csv}.")

    # Fast native C++ bulk load with explicit VARCHAR casting before TRIM
    conn.execute(f"""
        INSERT INTO normalized_events
        SELECT 
            source,
            TRY_CAST(NULLIF(TRIM(CAST(timestamp AS VARCHAR)), '') AS TIMESTAMP) AS timestamp_utc,
            NULLIF(TRIM(CAST(canonical AS VARCHAR)), '') AS canonical_name,
            NULLIF(TRIM(CAST(src_ip AS VARCHAR)), '') AS source_ip,
            NULLIF(TRIM(CAST(dst_ip AS VARCHAR)), '') AS destination_ip,
            NULLIF(TRIM(CAST(action AS VARCHAR)), '') AS action,
            NULLIF(TRIM(CAST(schema AS VARCHAR)), '') AS schema_version
        FROM read_csv('{temp_csv.as_posix()}', header=true, ignore_errors=true);
    """)

    # Clean up temp file
    try:
        temp_csv.unlink()
    except Exception:
        pass

    # Ensure output directory exists and handle file locks gracefully
    Path("output").mkdir(exist_ok=True)
    out_csv = Path("output/normalized-timeline.csv")
    try:
        if out_csv.exists():
            out_csv.unlink()
    except PermissionError:
        logger.warning("output/normalized-timeline.csv is locked. Writing to fallback file output/normalized-timeline_unlocked.csv instead!")
        out_csv = Path("output/normalized-timeline_unlocked.csv")

    logger.info(f"Exporting sorted timeline to {out_csv}...")
    conn.execute(f"""
        COPY (
            SELECT * FROM normalized_events 
            WHERE timestamp_utc IS NOT NULL 
            ORDER BY timestamp_utc
        ) TO '{out_csv.as_posix()}' (HEADER, DELIMITER ',');
    """)

    count = conn.execute("SELECT count(*) FROM normalized_events WHERE timestamp_utc IS NOT NULL;").fetchone()[0]
    logger.info(f"Success! {count:,} valid events normalized and exported. Quarantine log populated.")
    conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_correlation()