# Production Hunt Engine - Stage 1 Advanced Assessment Submission

## Overview
Production-grade log correlation pipeline, threat hunting engine, quarantine audit framework, and compliance registers developed for Stage 1 cybersecurity internship assessment.

## Repository URL
- **GitHub Repository:** [https://github.com/chinemerem-nsv/soc-hunt-engine](https://github.com/chinemerem-nsv/soc-hunt-engine)

## Clean-Build & Execution Instructions
To reproduce the entire build, database generation, normalization, hunting, and export from a clean state, run:

```bash
python hunt-engine/main.py
```

## Derived Outputs & Repository Structure
- `hunt-engine/`: Core execution scripts (`correlator.py`, `hunt_all.py`, `generate_deliverables.py`, `generate_manifests.py`, `main.py`).
- `tests/`: Automated test suite.
- `queries/`: SQL threat hunting scripts.
- Derived outputs (stored separately or generated via build pipeline): Master timeline (`normalized-timeline.csv`), DuckDB database (`clean.db`), benchmark reports, and compliance/cryptographic registers.