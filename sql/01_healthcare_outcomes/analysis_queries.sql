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


-- 30-day readmission rate per patient
WITH ordered_adm AS(
	SELECT
		a.*,
		ROW_NUMBER() OVER (
			PARTITION BY a.patient_id
            ORDER BY a.admission_date
		) AS rn
    FROM admissions a
),
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


-- View: latest admission per patient
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


-- Stored procedure: get summary by hospital
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

CALL sp_hospital_summary('Hospital_6');