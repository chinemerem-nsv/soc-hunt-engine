import subprocess
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("SOC_Master")

def run_script(script_path: Path):
    logger.info(f"Executing {script_path.name}...")
    result = subprocess.run([sys.executable, str(script_path)], capture_output=False)
    if result.returncode != 0:
        logger.error(f"Error executing {script_path.name}. Exiting pipeline.")
        sys.exit(result.returncode)

def main():
    logger.info("Starting Master SOC Pipeline Build...")
    src_dir = Path("src") # or hunt_engine if running from root post-packaging
    
    # Alternatively, if running from hunt-engine/ or root:
    # Let's target the scripts in order:
    steps = [
        Path("src/correlator.py"),
        Path("src/hunt_all.py"),
        Path("src/generate_deliverables.py"),
        Path("src/generate_manifests.py")
    ]
    
    for step in steps:
        if step.exists():
            run_script(step)
        else:
            logger.warning(f"Script {step} not found, checking local directory...")
            alt_step = Path("hunt-engine") / step.name
            if alt_step.exists():
                run_script(alt_step)
            else:
                logger.error(f"Critical script missing: {step.name}")
                sys.exit(1)

    print("\n" + "="*80)
    print(" MASTER PIPELINE BUILD & EXPORT COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()