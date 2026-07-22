import time
from pathlib import Path
import logging
from parser import parse_source_file
from normalizer import initialize_normalized_db
from validator import verify_reconciliation
import csv
import json

def main():
    start_time = time.time()
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("SOC_Main")
    
    logger.info("Starting SOC Advanced 1 pipeline execution...")

    # Ensure required directories exist
    Path("output").mkdir(exist_ok=True)
    Path("quarantine").mkdir(exist_ok=True)

    # Initialize DuckDB schema
    initialize_normalized_db()

    sources = ['auth', 'dns', 'endpoint', 'firewall', 'web']
    source_stats = {}
    all_quarantined = []

    for source in sources:
        logger.info(f"Processing source: {source}")
        accepted, quarantined = parse_source_file(source)
        source_stats[source] = {
            "accepted": len(accepted),
            "duplicates": 0,
            "quarantined": len(quarantined)
        }
        
        # Populate individual source quarantine jsonl files for sidebar sync
        q_file = Path(f"quarantine/quarantined_{source}.jsonl")
        with open(q_file, "w", encoding="utf-8") as f_q:
            for item in quarantined:
                f_q.write(item["raw"] + "\n")

        all_quarantined.extend(quarantined)

    # Write master quarantine log CSV
    if all_quarantined:
        with open("quarantine/quarantine_log.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["source", "line_number", "reason", "raw"])
            writer.writeheader()
            writer.writerows(all_quarantined)

    # Verify reconciliation
    verify_reconciliation(source_stats)

    elapsed = time.time() - start_time
    logger.info(f"Pipeline build successfully completed in {elapsed:.2f} seconds.")

if __name__ == "__main__":
    main()