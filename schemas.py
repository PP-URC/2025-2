REPORT_DBNAME = "reporte_asist_rend"
SURVEY_DBNAME = "encuesta"

REPORT_DB_SQL = """CREATE DATABASE IF NOT EXISTS reporte_asist_rend;
USE reporte_asist_rend;

CREATE TABLE IF NOT EXISTS estudiantes (
    matricula BIGINT PRIMARY KEY,
    nombre_completo VARCHAR(200) NOT NULL,
    grupo VARCHAR(50),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_grupo (grupo)
);

CREATE TABLE IF NOT EXISTS asistencia (
    id INT AUTO_INCREMENT PRIMARY KEY,
    matricula BIGINT,
    fecha DATE NOT NULL,
    presente BOOLEAN DEFAULT FALSE,
    materia VARCHAR(100),
    FOREIGN KEY (matricula) REFERENCES estudiantes(matricula),
    INDEX idx_matricula (matricula),  -- Keep this one
    INDEX idx_fecha (fecha)           -- Keep this one
);

CREATE TABLE IF NOT EXISTS evaluaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    matricula BIGINT,
    materia VARCHAR(100),
    tipo_evaluacion VARCHAR(50),
    calificacion DECIMAL(4,2),
    fecha_evaluacion DATE,
    FOREIGN KEY (matricula) REFERENCES estudiantes(matricula),
    INDEX idx_matricula (matricula)  -- Keep this one
);

CREATE TABLE IF NOT EXISTS reporte_estudiantes_problematicos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    matricula BIGINT,
    nombre_completo VARCHAR(200),
    grupo VARCHAR(50),
    promedio_general DECIMAL(4,2),
    tasa_asistencia DECIMAL(5,2),
    materia VARCHAR(100),
    problemas_detectados TEXT,
    gravedad ENUM('leve', 'moderado', 'grave', 'critico'),
    fecha_reporte TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (matricula) REFERENCES estudiantes(matricula)
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
    -- No indexes needed (small table)
);"""

SURVEY_DB_SQL = """DROP DATABASE IF EXISTS encuesta;
CREATE DATABASE IF NOT EXISTS encuesta;
USE encuesta;

CREATE TABLE carreras (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL
);

-- Table: unidades
CREATE TABLE unidades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_unidad VARCHAR(100)
);

-- Table: rangos_edad
CREATE TABLE rangos_edad (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rango VARCHAR(50)
);

-- Table: obstaculos
CREATE TABLE obstaculos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    obstaculo_desc VARCHAR(100) NOT NULL
);

CREATE TABLE tipos_trabajo (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tipo_trabajo VARCHAR(100)
);

CREATE TABLE niveles_adecuacion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nivel_adequacion VARCHAR(100)
);

CREATE TABLE factores_abandono (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre_factor VARCHAR(100) NOT NULL
);



-- Table: encuesta_desercion
CREATE TABLE encuesta_desercion (
    id INT PRIMARY KEY,
    continua_proximo_periodo BOOLEAN NOT NULL,
    id_rango_edad INT,
    id_unidad INT,
    id_carrera INT,
    semestre INT CHECK (semestre BETWEEN 1 AND 7),
    id_obstaculo INT,
    id_trabajo INT,
    identificacion INT CHECK (identificacion BETWEEN 0 AND 2),
    freq_sobrecargo INT CHECK (freq_sobrecargo BETWEEN 0 AND 2),
    frustracion_examenes BOOLEAN,
    freq_desanimo INT CHECK (freq_desanimo BETWEEN 0 AND 2),
    reprobo_materia BOOLEAN,
    id_nivel_adecuacion INT,
    id_factor_abandono INT,
    FOREIGN KEY (id_rango_edad) REFERENCES rangos_edad(id),
    FOREIGN KEY (id_unidad) REFERENCES unidades(id),
    FOREIGN KEY (id_obstaculo) REFERENCES obstaculos(id),
    FOREIGN KEY (id_trabajo) REFERENCES tipos_trabajo(id),
    FOREIGN KEY (id_carrera) REFERENCES carreras(id),
    FOREIGN KEY (id_factor_abandono) REFERENCES factores_abandono(id),
    FOREIGN KEY (id_nivel_adecuacion) REFERENCES niveles_adecuacion(id)
);"""
