import hashlib
import json
import csv
from pathlib import Path
import logging

logger = logging.getLogger("SOC_Manifests")

def compute_sha256(file_path: Path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in f:
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def generate_manifests():
    logger.info("Generating assessment manifest and evidence index...")
    output_dir = Path("output")
    quarantine_dir = Path("quarantine")

    files_to_index = [
        output_dir / "normalized-timeline.csv",
        output_dir / "campaign1_initial_access.csv",
        output_dir / "campaign2_lateral_movement.csv",
        output_dir / "campaign3_exfiltration_c2.csv",
        output_dir / "data-quality-register.csv",
        output_dir / "benchmark.json",
        quarantine_dir / "quarantine_log.csv"
    ]

    manifest_data = {"artifacts": []}
    evidence_rows = []

    for file_path in files_to_index:
        if file_path.exists():
            file_size = file_path.stat().st_size
            file_hash = compute_sha256(file_path)
            
            manifest_data["artifacts"].append({
                "file_name": file_path.name,
                "path": file_path.as_posix(),
                "size_bytes": file_size,
                "sha256": file_hash
            })
            
            evidence_rows.append([
                file_path.name,
                file_path.parent.name,
                "Verified artifact produced by hunt pipeline",
                file_hash
            ])

    # Write assessment-manifest.json
    manifest_path = output_dir / "assessment-manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest_data, mf, indent=4)
    logger.info(f"Assessment manifest exported to {manifest_path}")

    # Write evidence-index.csv
    evidence_index_path = output_dir / "evidence-index.csv"
    with open(evidence_index_path, "w", encoding="utf-8", newline="") as ei:
        writer = csv.writer(ei)
        writer.writerow(["file_name", "directory", "description", "sha256_hash"])
        writer.writerows(evidence_rows)
    logger.info(f"Evidence index exported to {evidence_index_path}")

    print("\n" + "="*80)
    print(" FINAL MANIFESTS GENERATION COMPLETE")
    print("="*80)
    print(f"[+] Assessment Manifest : {manifest_path}")
    print(f"[+] Evidence Index      : {evidence_index_path}")
    print("="*80 + "\n")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_manifests()