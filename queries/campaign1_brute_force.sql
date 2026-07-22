SELECT source_ip, COUNT(*) as total_events, 
SUM(CASE WHEN action ILIKE '%fail%' OR action ILIKE '%deny%' THEN 1 ELSE 0 END) as failure_count 
FROM normalized_events WHERE source = 'auth' GROUP BY source_ip HAVING failure_count > 5 ORDER BY failure_count DESC;