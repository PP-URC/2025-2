CREATE DATABASE {assist_eval_db_name};
USE {assist_eval_db_name};

CREATE TABLE IF NOT EXISTS estudiantes (
    matricula BIGINT PRIMARY KEY,
    nombre_completo VARCHAR(200) NOT NULL,
    grupo VARCHAR(50),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS asistencia (
    matricula INT AUTO_INCREMENT PRIMARY KEY,
    fecha DATE NOT NULL,
    presente BOOLEAN DEFAULT FALSE,
    materia VARCHAR(100),
    FOREIGN KEY (matricula) REFERENCES estudiantes(matricula)
);

CREATE TABLE IF NOT EXISTS evaluaciones (
    matricula BIGINT AUTO_INCREMENT PRIMARY KEY,
    materia VARCHAR(100),
    tipo_evaluacion VARCHAR(50),  -- 'Parcial 1', 'Tarea', 'Examen Final'
    calificacion DECIMAL(4,2),
    fecha_evaluacion DATE,
    FOREIGN KEY (matricula) REFERENCES estudiantes(matricula)
);

CREATE TABLE IF NOT EXISTS reporte_estudiantes_problematicos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    matricula BIGINT,
    nombre_completo VARCHAR(200),
    grupo VARCHAR(50),
    promedio_general DECIMAL(4,2),
    tasa_asistencia DECIMAL(5,2),
    materias_reprobadas INT DEFAULT 0,
    problemas_detectados TEXT,
    gravedad ENUM('leve', 'moderado', 'grave', 'critico'),
    fecha_reporte TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_gravedad (gravedad),
    INDEX idx_grupo (grupo)
);

CREATE TABLE IF NOT EXISTS reporte_grupos_problematicos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    grupo VARCHAR(50),
    total_estudiantes INT,
    estudiantes_problematicos INT,
    promedio_grupo DECIMAL(4,2),
    tasa_asistencia_grupo DECIMAL(5,2),
    problemas_comunes TEXT,
    fecha_reporte TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
