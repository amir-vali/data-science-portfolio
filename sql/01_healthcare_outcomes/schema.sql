-- Drop tables if they exist (for re-run)
DROP TABLE IF EXISTS diagnoses;
DROP TABLE IF EXISTS admissions;
DROP TABLE IF EXISTS patients;

-- Patients table
CREATE TABLE patients (
    patient_id      INT PRIMARY KEY AUTO_INCREMENT,
    first_name      VARCHAR(50),
    last_name       VARCHAR(50),
    birth_date      DATE,
    gender          ENUM('M', 'F', 'Other')
);

-- Admissions table
CREATE TABLE admissions (
    admission_id    INT PRIMARY KEY AUTO_INCREMENT,
    patient_id      INT NOT NULL,
    admission_date  DATE NOT NULL,
    discharge_date  DATE,
    outcome         ENUM('Recovered', 'Readmitted', 'Deceased') NOT NULL,
    hospital        VARCHAR(100),
    CONSTRAINT fk_admissions_patient
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

-- Diagnoses table
CREATE TABLE diagnoses (
    diagnosis_id    INT PRIMARY KEY AUTO_INCREMENT,
    admission_id    INT NOT NULL,
    icd_code        VARCHAR(10) NOT NULL,
    is_primary      BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_diagnoses_admission
        FOREIGN KEY (admission_id) REFERENCES admissions(admission_id)
);
