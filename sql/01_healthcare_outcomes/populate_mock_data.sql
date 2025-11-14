-- Assumes the database and tables from schema.sql already exist
-- Run: USE hospital_db; then SOURCE populate_mock_data.sql;

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE diagnoses;
TRUNCATE TABLE admissions;
TRUNCATE TABLE patients;
SET FOREIGN_KEY_CHECKS = 1;

DELIMITER $$


-- 1) Populate patients


DROP PROCEDURE IF EXISTS populate_patients$$
CREATE PROCEDURE populate_patients(IN p_count INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE v_birth DATE;
    DECLARE v_gender ENUM('M','F','Other');

    WHILE i <= p_count DO
        -- random birth date between 1940-01-01 and 2010-12-31
        SET v_birth = DATE_ADD('1940-01-01', INTERVAL FLOOR(RAND() * 26000) DAY);

        -- random gender
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



-- 2) Populate admissions


DROP PROCEDURE IF EXISTS populate_admissions$$
CREATE PROCEDURE populate_admissions(IN a_count INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE v_patient_id INT;
    DECLARE v_adm_date DATE;
    DECLARE v_dis_date DATE;
    DECLARE v_outcome ENUM('Recovered','Readmitted','Deceased');
    DECLARE v_max_patient_id INT;

    -- we assume patient_id values are dense from 1..max_id
    SELECT MAX(patient_id) INTO v_max_patient_id FROM patients;

    WHILE i <= a_count DO
        -- random patient id
        SET v_patient_id = FLOOR(1 + RAND() * v_max_patient_id);

        -- random admission date between 2018-01-01 and 2024-12-31
        SET v_adm_date = DATE_ADD('2018-01-01', INTERVAL FLOOR(RAND() * 2550) DAY);

        -- 15% chance of still hospitalized (no discharge_date yet)
        IF RAND() < 0.15 THEN
            SET v_dis_date = NULL;
        ELSE
            -- discharge date 0–20 days after admission
            SET v_dis_date = DATE_ADD(v_adm_date, INTERVAL FLOOR(RAND() * 21) DAY);
        END IF;

        -- outcome (simplified, not strictly consistent with NULL discharge)
        SET v_outcome = ELT(
            FLOOR(1 + RAND() * 3),
            'Recovered',
            'Readmitted',
            'Deceased'
        );

        INSERT INTO admissions (patient_id, admission_date, discharge_date, outcome, hospital)
        VALUES (
            v_patient_id,
            v_adm_date,
            v_dis_date,
            v_outcome,
            CONCAT('Hospital_', FLOOR(1 + RAND() * 10))
        );

        SET i = i + 1;
    END WHILE;
END$$



-- 3) Populate diagnoses


DROP PROCEDURE IF EXISTS populate_diagnoses$$
CREATE PROCEDURE populate_diagnoses(IN d_count INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE v_admission_id INT;
    DECLARE v_max_adm_id INT;
    DECLARE v_icd_code VARCHAR(10);
    DECLARE v_is_primary BOOLEAN;

    SELECT MAX(admission_id) INTO v_max_adm_id FROM admissions;

    WHILE i <= d_count DO
        -- random admission id
        SET v_admission_id = FLOOR(1 + RAND() * v_max_adm_id);

        -- random ICD code from a small realistic list
        SET v_icd_code = ELT(
            FLOOR(1 + RAND() * 10),
            'I10',   -- essential hypertension
            'E11',   -- type 2 diabetes
            'J20',   -- acute bronchitis
            'K35',   -- acute appendicitis
            'N39',   -- urinary tract infection
            'C50',   -- breast cancer
            'F32',   -- depressive episode
            'M54',   -- dorsalgia
            'R51',   -- headache
            'A09'    -- infectious gastroenteritis
        );

        -- ~40% primary diagnoses
        SET v_is_primary = (RAND() < 0.4);

        INSERT INTO diagnoses (admission_id, icd_code, is_primary)
        VALUES (
            v_admission_id,
            v_icd_code,
            v_is_primary
        );

        SET i = i + 1;
    END WHILE;
END$$

DELIMITER ;



-- Execute population



CALL populate_patients(200);
CALL populate_admissions(600);
CALL populate_diagnoses(1200);
