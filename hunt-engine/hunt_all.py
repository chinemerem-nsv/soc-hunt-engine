import duckdb
from pathlib import Path
import logging

logger = logging.getLogger("SOC_UnifiedHuntEngine")

def run_all_hunts(db_path: Path = Path("clean.db")):
    conn = duckdb.connect(str(db_path))
    logger.info("Executing Unified Hunt Engine across all security telemetry...")

    Path("output").mkdir(exist_ok=True)

    # ==========================================
    # CAMPAIGN 1: Initial Access & Brute-Forcing
    # ==========================================
    logger.info("Running Campaign 1 Hunt: Authentication Brute-Force & Credential Stuffing...")
    q1 = """
        SELECT 
            source_ip,
            COUNT(*) as total_events,
            SUM(CASE WHEN action ILIKE '%fail%' OR action ILIKE '%deny%' OR action ILIKE '%invalid%' THEN 1 ELSE 0 END) as failure_count,
            SUM(CASE WHEN action ILIKE '%success%' OR action ILIKE '%allow%' OR action ILIKE '%login_ok%' THEN 1 ELSE 0 END) as success_count,
            MIN(timestamp_utc) as first_seen,
            MAX(timestamp_utc) as last_seen,
            STRING_AGG(DISTINCT canonical_name, ', ') as targeted_users
        FROM normalized_events
        WHERE source = 'auth'
        GROUP BY source_ip
        HAVING failure_count > 5
        ORDER BY failure_count DESC
        LIMIT 5
    """
    res1 = conn.execute(q1).fetchall()
    conn.execute(f"COPY ({q1}) TO 'output/campaign1_initial_access.csv' (HEADER, DELIMITER ',');")

    # ==========================================
    # CAMPAIGN 2: Lateral Movement & Endpoint Activity (Broadened)
    # ==========================================
    logger.info("Running Campaign 2 Hunt: Lateral Movement & Suspicious Endpoint Execution...")
    q2 = """
        SELECT 
            COALESCE(canonical_name, 'Unknown_Asset') as asset_or_user,
            COALESCE(source_ip, 'N/A') as source_ip,
            COALESCE(destination_ip, 'N/A') as destination_ip,
            COALESCE(action, 'N/A') as process_or_event,
            COUNT(*) as event_frequency,
            MIN(timestamp_utc) as first_seen,
            MAX(timestamp_utc) as last_seen
        FROM normalized_events
        WHERE source IN ('endpoint', 'firewall')
        GROUP BY canonical_name, source_ip, destination_ip, action
        ORDER BY event_frequency DESC
        LIMIT 5
    """
    res2 = conn.execute(q2).fetchall()
    conn.execute(f"COPY ({q2}) TO 'output/campaign2_lateral_movement.csv' (HEADER, DELIMITER ',');")

    # ==========================================
    # CAMPAIGN 3: C2 & Data Exfiltration / DNS Anomalies
    # ==========================================
    logger.info("Running Campaign 3 Hunt: Command & Control (C2) / Data Exfiltration via DNS & Web...")
    q3 = """
        SELECT 
            COALESCE(canonical_name, 'Unknown_Query') as query_domain,
            COALESCE(source_ip, 'N/A') as source_ip,
            COALESCE(destination_ip, 'N/A') as destination_ip,
            COALESCE(action, 'N/A') as action,
            COUNT(*) as request_count,
            MIN(timestamp_utc) as first_seen
        FROM normalized_events
        WHERE source IN ('dns', 'web')
        GROUP BY canonical_name, source_ip, destination_ip, action
        HAVING request_count > 10
        ORDER BY request_count DESC
        LIMIT 5
    """
    res3 = conn.execute(q3).fetchall()
    conn.execute(f"COPY ({q3}) TO 'output/campaign3_exfiltration_c2.csv' (HEADER, DELIMITER ',');")

    # ==========================================
    # Console Reporting Dashboard
    # ==========================================
    print("\n" + "="*95)
    print(" UNIFIED SOC HUNT ENGINE RESULTS - ALL CAMPAIGNS")
    print("="*95)

    print("\n[+] CAMPAIGN 1: Initial Access / Brute-Force Suspects")
    print(f"{'Source IP':<18} | {'Failures':<10} | {'Successes':<10} | {'Targeted Users'}")
    print("-" * 95)
    for row in res1:
        print(f"{row[0] or 'N/A':<18} | {row[2]:<10} | {row[3]:<10} | {row[6]}")

    print("\n[+] CAMPAIGN 2: Lateral Movement & Endpoint Activity")
    print(f"{'Asset/User':<18} | {'Src IP':<15} | {'Dst IP':<15} | {'Process/Event'}")
    print("-" * 95)
    for row in res2:
        print(f"{row[0] or 'N/A':<18} | {row[1] or 'N/A':<15} | {row[2] or 'N/A':<15} | {row[3]} ({row[4]} events)")

    print("\n[+] CAMPAIGN 3: C2 / Data Exfiltration (DNS & Web Anomalies)")
    print(f"{'Query/Domain':<25} | {'Src IP':<15} | {'Dst IP':<15} | {'Count'}")
    print("-" * 95)
    for row in res3:
        print(f"{row[0] or 'N/A':<25} | {row[1] or 'N/A':<15} | {row[2] or 'N/A':<15} | {row[4]}")

    print("="*95)
    logger.info("All campaign queries executed successfully. Artifacts exported to output/ directory.")
    conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_all_hunts()