/*
 * Analysis Queries - Healthcare Outcomes Analysis
 * Analytical queries for mortality rates, length of stay, readmissions, and hospital performance
 * See README.md for full documentation and query explanations
 */

-- Query 1: Mortality rate by primary diagnosis
-- Analyzes which conditions have the highest mortality rates using primary diagnoses only
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


-- Query 2: Average length of stay by hospital and diagnosis
-- Compares LOS across hospitals for the same primary diagnosis
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


-- Query 3: 30-day readmission rate calculation
-- Uses window functions to identify patients readmitted within 30 days of discharge
-- CTE 1: Orders admissions chronologically per patient using ROW_NUMBER
WITH ordered_adm AS(
	SELECT
		a.*,
		ROW_NUMBER() OVER (
			PARTITION BY a.patient_id
            ORDER BY a.admission_date
		) AS rn
    FROM admissions a
),
-- CTE 2: Pairs consecutive admissions to calculate days between discharge and next admission
pairs AS (
	SELECT
		cur.patient_id,
		cur.admission_date AS index_admission,
        nxt.admission_date AS next_admission,
        DATEDIFF(nxt.admission_date, cur.discharge_date) AS days_between
    FROM ordered_adm cur
    LEFT JOIN ordered_adm nxt
		ON cur.patient_id = nxt.patient_id
		AND cur.rn + 1 = nxt.rn
)
SELECT
	COUNT(*) AS index_admissions,
    SUM(CASE WHEN days_between BETWEEN 0 AND 30 THEN 1 ELSE 0 END) AS readmission_30d,
    ROUND(
		100.0 * SUM(CASE WHEN days_between BETWEEN 0 AND 30 THEN 1 ELSE 0 END) / COUNT(*),
        2
	) AS readmission_rate_30d_pct
FROM pairs;


-- Query 4: View - Latest admission per patient
-- Creates a reusable view showing the most recent admission for each patient
-- Uses window function to rank admissions by date (most recent first)
CREATE OR REPLACE VIEW v_latest_admission AS
SELECT *
FROM (
	SELECT
		a.*,
		ROW_NUMBER() OVER (
			PARTITION BY patient_id
			ORDER BY admission_date DESC
		) AS rn
	FROM admissions a
) t
WHERE t.rn = 1;

SELECT * FROM v_latest_admission;


-- Query 5: Stored procedure - Hospital performance summary
-- Returns mortality statistics for a specific hospital (admission count, deaths, mortality rate)
DELIMITER $$
CREATE PROCEDURE sp_hospital_summary (IN p_hospital VARCHAR(100))
BEGIN
	SELECT
		hospital,
        COUNT(*) AS admissions_count,
        SUM(CASE WHEN outcome = 'Deceased' THEN 1 ELSE 0 END) AS deaths,
        ROUND(
			100.0 * SUM(CASE WHEN outcome = 'Deceased' THEN 1 ELSE 0 END) / COUNT(*),
            2
        ) AS mortality_rate_pct
    FROM admissions
    WHERE hospital = p_hospital
    GROUP BY hospital;
END$$
DELIMITER ;

-- Example: Get summary for a specific hospital
CALL sp_hospital_summary('Hospital_6');