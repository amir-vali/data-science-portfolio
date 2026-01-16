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


-- Query 3: 30-day readmission and anytime readmission rates calculation
-- Uses window functions to identify patients readmitted within 30 days of discharge and anytime after discharge
WITH ordered_adm AS (
  SELECT
    a.*,
    LEAD(admission_date) OVER (PARTITION BY patient_id ORDER BY admission_date) AS next_admission_date
  FROM admissions a
),
pairs AS (
  SELECT
    patient_id,
    admission_id,
    outcome,
    discharge_date,
    next_admission_date,
    DATEDIFF(next_admission_date, discharge_date) AS days_between
  FROM ordered_adm
)
SELECT
  COUNT(*) AS eligible_admissions,
  SUM(CASE WHEN outcome = 'Readmitted' THEN 1 ELSE 0 END) AS readmitted_any_time,
  SUM(CASE WHEN days_between BETWEEN 0 AND 30 THEN 1 ELSE 0 END) AS readmitted_30d,
  ROUND(100.0 * SUM(CASE WHEN outcome = 'Readmitted' THEN 1 ELSE 0 END) / COUNT(*), 2) AS readmitted_any_time_pct,
  ROUND(100.0 * SUM(CASE WHEN days_between BETWEEN 0 AND 30 THEN 1 ELSE 0 END) / COUNT(*), 2) AS readmitted_30d_pct
FROM pairs
WHERE outcome <> 'Deceased'
  AND discharge_date IS NOT NULL
  AND next_admission_date IS NOT NULL
  AND days_between >= 0;




-- Query 4: View - Latest admission per patient
-- Creates a reusable view showing the most recent admission for each patient
-- Uses window function to rank admissions by date (most recent first)
CREATE OR REPLACE VIEW v_latest_admission AS
SELECT admission_id, patient_id, admission_date, discharge_date, outcome, hospital
FROM (
  SELECT
    a.*,
    ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY admission_date DESC) AS rn
  FROM admissions a
) t
WHERE t.rn = 1;

SELECT * FROM v_latest_admission;


-- Query 5: Stored procedure - Hospital performance summary
-- Returns mortality statistics for a specific hospital (admission count, deaths, mortality rate)
DROP PROCEDURE IF EXISTS sp_hospital_summary;
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