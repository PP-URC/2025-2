DROP DATABASE IF EXISTS encuesta;
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
);
