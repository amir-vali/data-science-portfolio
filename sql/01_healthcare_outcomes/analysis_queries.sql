-- Admissions per primary diagnosis with mortality rate

WITH primary_diag AS (
    SELECT
        d.admission_id,
        d.icd_code
    FROM diagnoses d
    WHERE d.is_primary = TRUE
)
SELECT
    p.icd_code,
    COUNT(*) AS admissions_count,
    SUM(CASE WHEN a.outcome = 'Deceased' THEN 1 ELSE 0 END) AS deaths,
    ROUND(
        100.0 * SUM(CASE WHEN a.outcome = 'Deceased' THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS mortality_rate_pct
FROM primary_diag p
JOIN admissions a ON a.admission_id = p.admission_id
GROUP BY p.icd_code
ORDER BY mortality_rate_pct DESC;


-- Average length of stay (LOS) per hospital & diagnosis

WITH primary_diag AS (
    SELECT
        d.admission_id,
        d.icd_code
    FROM diagnoses d
    WHERE d.is_primary = TRUE
)
SELECT
    a.hospital,
    p.icd_code,
    AVG(DATEDIFF(a.discharge_date, a.admission_date)) AS avg_los_days
FROM primary_diag p
JOIN admissions a ON a.admission_id = p.admission_id
GROUP BY a.hospital, p.icd_code
ORDER BY avg_los_days DESC;


