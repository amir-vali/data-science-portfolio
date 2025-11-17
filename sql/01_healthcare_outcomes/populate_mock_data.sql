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
-- Random assignment to patients, dates 2018-2024, LOS 0-20 days, 15% active admissions
DROP PROCEDURE IF EXISTS populate_admissions$$
CREATE PROCEDURE populate_admissions(IN a_count INT)
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE v_patient_id INT;
    DECLARE v_adm_date DATE;
    DECLARE v_dis_date DATE;
    DECLARE v_outcome ENUM('Recovered','Readmitted','Deceased');
    DECLARE v_max_patient_id INT;

    SELECT MAX(patient_id) INTO v_max_patient_id FROM patients;

    WHILE i <= a_count DO
        -- Random patient ID (allows multiple admissions per patient)
        SET v_patient_id = FLOOR(1 + RAND() * v_max_patient_id);

        -- Random admission date: 2018-2024 (~7 years of data)
        SET v_adm_date = DATE_ADD('2018-01-01', INTERVAL FLOOR(RAND() * 2550) DAY);

        -- 15% have NULL discharge_date (active admissions), else LOS 0-20 days
        IF RAND() < 0.15 THEN
            SET v_dis_date = NULL;
        ELSE
            SET v_dis_date = DATE_ADD(v_adm_date, INTERVAL FLOOR(RAND() * 21) DAY);
        END IF;

        -- Random outcome: Recovered, Readmitted, or Deceased
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



-- Procedure: populate_diagnoses - Generates diagnosis records with ICD-10 codes
-- Random assignment to admissions, ~40% primary diagnoses, covers multiple specialties
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
        -- Random admission ID (allows multiple diagnoses per admission)
        SET v_admission_id = FLOOR(1 + RAND() * v_max_adm_id);

        -- Random ICD-10 code from common conditions (hypertension, diabetes, etc.)
        SET v_icd_code = ELT(
            FLOOR(1 + RAND() * 10),
            'I10',   -- Essential hypertension
            'E11',   -- Type 2 diabetes
            'J20',   -- Acute bronchitis
            'K35',   -- Acute appendicitis
            'N39',   -- Urinary tract infection
            'C50',   -- Breast cancer
            'F32',   -- Depressive episode
            'M54',   -- Dorsalgia
            'R51',   -- Headache
            'A09'    -- Infectious gastroenteritis
        );

        -- ~40% are primary diagnoses
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

-- Execute data population (adjust counts as needed)

CALL populate_patients(200);
CALL populate_admissions(600);
CALL populate_diagnoses(1200);
