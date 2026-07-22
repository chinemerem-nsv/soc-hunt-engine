import json
from pathlib import Path
import logging

logger = logging.getLogger("SOC_Parser")

def parse_source_file(source_name: str, evidence_dir: Path = Path("evidence")):
    log_file = evidence_dir / f"{source_name}.jsonl"
    accepted = []
    quarantined = []
    duplicates = set()
    
    if not log_file.exists():
        logger.warning(f"Source file not found: {log_file}")
        return accepted, quarantined

    with open(log_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            raw_line = line.strip()
            if not raw_line:
                continue
                
            if raw_line in duplicates:
                continue
            duplicates.add(raw_line)

            try:
                data = json.loads(raw_line)
            except json.JSONDecodeError:
                quarantined.append({
                    "source": source_name,
                    "line_number": line_num,
                    "reason": "json_decode_error",
                    "raw": raw_line
                })
                continue

            # Schema version validation
            if not data.get("schema_version"):
                quarantined.append({
                    "source": source_name,
                    "line_number": line_num,
                    "reason": "missing_schema_version",
                    "raw": raw_line
                })
                continue

            accepted.append(data)

    return accepted, quarantined