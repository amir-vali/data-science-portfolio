/*
 * Populate Mock Data - Automated data generation using stored procedures
 * Generates randomized mock dataset for testing (200 patients, 600 admissions, 1200 diagnoses)
 * See README.md for full documentation and usage instructions
 */

-- Temporarily disable foreign key checks to allow truncation in any order
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE diagnoses;
TRUNCATE TABLE admissions;
TRUNCATE TABLE patients;
SET FOREIGN_KEY_CHECKS = 1;

DELIMITER $$

-- Procedure: populate_patients - Generates patient records with randomized demographics
-- Creates patients with random birth dates (ages ~14-84) and gender distribution
DROP PROCEDURE IF EXISTS populate_patients$$
CREATE PROCEDURE populate_patients(IN p_count INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE v_birth DATE;
    DECLARE v_gender ENUM('M','F','Other');

    WHILE i <= p_count DO
        -- Random birth date: 1940-2010 (ages ~14-84 as of 2024)
        SET v_birth = DATE_ADD('1940-01-01', INTERVAL FLOOR(RAND() * 26000) DAY);

        -- Random gender selection
        SET v_gender = ELT(FLOOR(1 + RAND() * 3), 'M', 'F', 'Other');

        INSERT INTO patients (first_name, last_name, birth_date, gender)
        VALUES (
            CONCAT('Name_', i),
            CONCAT('Family_', i),
            v_birth,
            v_gender
        );

        SET i = i + 1;
    END WHILE;
END$$



-- Procedure: populate_admissions - Generates admission records
DROP PROCEDURE IF EXISTS populate_admissions$$
CREATE PROCEDURE populate_admissions(IN a_count INT)
BEGIN
    DECLARE i INT DEFAULT 1;

    DECLARE v_patient_id INT;
    DECLARE v_adm_date DATE;
    DECLARE v_dis_date DATE;

    DECLARE v_outcome VARCHAR(20);
    DECLARE v_hospital VARCHAR(100);

    DECLARE v_max_patient_id INT;
    DECLARE v_last_discharge DATE;
    DECLARE v_is_alive TINYINT;

    DECLARE v_gap_days INT;
    DECLARE v_los_days INT;

    DECLARE v_attempts INT;

    SELECT MAX(patient_id) INTO v_max_patient_id FROM patients;

    -- Track each patient's last discharge and alive status to avoid overlaps and post-death admissions
    DROP TEMPORARY TABLE IF EXISTS tmp_patient_state;
    CREATE TEMPORARY TABLE tmp_patient_state (
        patient_id INT PRIMARY KEY,
        last_discharge DATE NOT NULL,
        is_alive TINYINT NOT NULL DEFAULT 1
    );

    -- Initialize last_discharge to a date before the generation window
    INSERT INTO tmp_patient_state (patient_id, last_discharge, is_alive)
    SELECT
        p.patient_id,
        DATE_ADD('2017-01-01', INTERVAL FLOOR(RAND() * 365) DAY),
        1
    FROM patients p;

    main_loop: WHILE i <= a_count DO

        SET v_attempts = 0;

        -- Pick an alive patient (retry a few times)
        pick_patient: LOOP
            SET v_patient_id = FLOOR(1 + RAND() * v_max_patient_id);

            SELECT last_discharge, is_alive
              INTO v_last_discharge, v_is_alive
            FROM tmp_patient_state
            WHERE patient_id = v_patient_id;

            IF v_is_alive = 1 THEN
                LEAVE pick_patient;
            END IF;

            SET v_attempts = v_attempts + 1;
            IF v_attempts >= 20 THEN
                -- Fallback: stop trying too hard; break to avoid infinite loops
                LEAVE pick_patient;
            END IF;
        END LOOP;

        -- If the chosen patient is not alive (fallback case), pick next iteration
        IF v_is_alive <> 1 THEN
            SET i = i + 1;
            ITERATE main_loop;
        END IF;

        -- Generate a non-overlapping admission after last discharge
        SET v_gap_days = FLOOR(1 + RAND() * 180);   -- 1..180 days gap
        SET v_adm_date = DATE_ADD(v_last_discharge, INTERVAL v_gap_days DAY);

        -- Keep within the target window (2018-2024)
        IF v_adm_date < '2018-01-01' THEN
            SET v_adm_date = '2018-01-01';
        END IF;

        IF v_adm_date > '2024-12-15' THEN
            -- If we are too late in the timeline, restart this patient's timeline earlier
            SET v_last_discharge = DATE_ADD('2017-01-01', INTERVAL FLOOR(RAND() * 365) DAY);
            UPDATE tmp_patient_state
               SET last_discharge = v_last_discharge
             WHERE patient_id = v_patient_id;

            ITERATE main_loop;
        END IF;

        -- Length of stay: 1..20 days
        SET v_los_days = FLOOR(1 + RAND() * 20);
        SET v_dis_date = DATE_ADD(v_adm_date, INTERVAL v_los_days DAY);

        -- Outcome distribution (Deceased should be relatively rare)
		IF RAND() < 0.05 THEN
		  SET v_outcome = 'Deceased';
		ELSE
		  SET v_outcome = 'Recovered';
		END IF;

        SET v_hospital = CONCAT('Hospital_', FLOOR(1 + RAND() * 10));

        INSERT INTO admissions (patient_id, admission_date, discharge_date, outcome, hospital)
        VALUES (v_patient_id, v_adm_date, v_dis_date, v_outcome, v_hospital);

        -- Update patient state
        UPDATE tmp_patient_state
           SET last_discharge = v_dis_date
         WHERE patient_id = v_patient_id;

        -- If deceased, mark patient as not alive to prevent future admissions
        IF v_outcome = 'Deceased' THEN
            UPDATE tmp_patient_state
               SET is_alive = 0
             WHERE patient_id = v_patient_id;
        END IF;

        SET i = i + 1;
    END WHILE;

END$$


-- Procedure: derive_outcomes_from_sequences - relable readmitted patient's outcome
DROP PROCEDURE IF EXISTS derive_outcomes_from_sequences$$
CREATE PROCEDURE derive_outcomes_from_sequences()
BEGIN
  /*
    Sets outcome='Readmitted' if the admission has a subsequent admission
    for the same patient (any time after discharge/admission sequence).
    Keeps 'Deceased' unchanged.
  */

  WITH next_adm AS (
    SELECT
      admission_id,
      LEAD(admission_id) OVER (PARTITION BY patient_id ORDER BY admission_date) AS next_admission_id
    FROM admissions
  )
  UPDATE admissions a
  JOIN next_adm n ON a.admission_id = n.admission_id
  SET a.outcome =
    CASE
      WHEN a.outcome = 'Deceased' THEN 'Deceased'
      WHEN n.next_admission_id IS NOT NULL THEN 'Readmitted'
      ELSE 'Recovered'
    END;
END$$


-- Procedure: populate_diagnoses - Generates diagnosis records with ICD-10 codes
DROP PROCEDURE IF EXISTS populate_diagnoses$$
CREATE PROCEDURE populate_diagnoses(IN d_count INT)
BEGIN
    DECLARE v_admission_id INT DEFAULT 1;
    DECLARE v_max_adm_id INT;
    DECLARE v_icd_code VARCHAR(10);

    DECLARE v_inserted INT DEFAULT 0;
    DECLARE v_target INT;

    SELECT MAX(admission_id) INTO v_max_adm_id FROM admissions;

    -- Ensure we can at least insert one primary per admission
    SET v_target = d_count;
    IF v_target < v_max_adm_id THEN
        SET v_target = v_max_adm_id;
    END IF;

    -- Helper: pick a random ICD-10 code
    -- (We'll just repeat the ELT block each time for simplicity)

    -- Pass 1: exactly one primary diagnosis per admission
    SET v_admission_id = 1;
    WHILE v_admission_id <= v_max_adm_id DO

        SET v_icd_code = ELT(
            FLOOR(1 + RAND() * 10),
            'I10','E11','J20','K35','N39','C50','F32','M54','R51','A09'
        );

        INSERT INTO diagnoses (admission_id, icd_code, is_primary)
        VALUES (v_admission_id, v_icd_code, 1);

        SET v_inserted = v_inserted + 1;
        SET v_admission_id = v_admission_id + 1;
    END WHILE;

    -- Pass 2: add secondary diagnoses until reaching target count
    WHILE v_inserted < v_target DO

        SET v_admission_id = FLOOR(1 + RAND() * v_max_adm_id);

        SET v_icd_code = ELT(
            FLOOR(1 + RAND() * 10),
            'I10','E11','J20','K35','N39','C50','F32','M54','R51','A09'
        );

        INSERT INTO diagnoses (admission_id, icd_code, is_primary)
        VALUES (v_admission_id, v_icd_code, 0);

        SET v_inserted = v_inserted + 1;
    END WHILE;

END$$


DELIMITER ;

-- Execute data population (adjust counts as needed)

CALL populate_patients(200);
CALL populate_admissions(600);
CALL populate_diagnoses(1200);
CALL derive_outcomes_from_sequences();
