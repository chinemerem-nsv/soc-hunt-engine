import duckdb
import json
from pathlib import Path
import time
import logging

logger = logging.getLogger("SOC_Pipeline")

def run_pipeline():
    start_time = time.time()
    db_path = Path("clean.db")
    if db_path.exists():
        db_path.unlink() # Fresh deterministic build

    conn = duckdb.connect(str(db_path))
    
    quarantine_records = []
    reconciliation_data = {}

    sources = ['auth', 'dns', 'endpoint', 'firewall', 'web']
    
    for source in sources:
        log_file = Path(f"evidence/{source}.jsonl")
        if not log_file.exists():
            logger.warning(f"Evidence file missing: {log_file}")
            continue

        logger.info(f"Processing {source}.jsonl...")
        
        accepted_count = 0
        quarantined_count = 0
        duplicate_count = 0
        seen_rows = set()

        with open(log_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                raw_line = line.strip()
                if not raw_line:
                    continue
                
                # Check for duplicate raw rows
                if raw_line in seen_rows:
                    duplicate_count += 1
                    continue
                seen_rows.add(raw_line)

                try:
                    data = json.loads(raw_line)
                except json.JSONDecodeError:
                    quarantined_count += 1
                    quarantine_records.append({
                        "source": source,
                        "line_number": line_num,
                        "reason": "json_decode_error",
                        "raw": raw_line
                    })
                    continue

                # Schema version check
                version = data.get("schema_version")
                if not version:
                    quarantined_count += 1
                    quarantine_records.append({
                        "source": source,
                        "line_number": line_num,
                        "reason": "missing_schema_version",
                        "raw": raw_line
                    })
                    continue

                accepted_count += 1

        reconciliation_data[source] = {
            "accepted": accepted_count,
            "duplicates": duplicate_count,
            "quarantined": quarantined_count,
            "total_accounted": accepted_count + duplicate_count + quarantined_count
        }

    # Save reconciliation summary
    with open("reconciliation.json", "w") as f_rec:
        json.dump(reconciliation_data, f_rec, indent=2)

    elapsed = time.time() - start_time
    logger.info(f"Pipeline execution completed in {elapsed:.2f} seconds.")
    conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_pipeline()