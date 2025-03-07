CREATE DATABASE civic_db;

GRANT ALL ON DATABASE civic_db TO civic_db_admin;

\connect civic_db;

-- SET TIMEZONE (America/New_York)

ALTER DATABASE civic_db SET timezone TO 'UTC';

CREATE TABLE models (
    id SERIAL PRIMARY KEY,
    model_id INTEGER NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    status INTEGER NOT NULL DEFAULT 1 -- 0: inactive, 1: active
); 

CREATE TABLE model_binaries (
    id SERIAL PRIMARY KEY,
    model_id INTEGER NOT NULL REFERENCES models(model_id),
    version INTEGER NOT NULL,
    binary_data bytea NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE FUNCTION create_model_related_tables() RETURNS TRIGGER AS $$
BEGIN
    EXECUTE format('
        CREATE TABLE model_%s_data (
            id SERIAL PRIMARY KEY,
            model_id INTEGER NOT NULL REFERENCES models(model_id),
            fragment_id INTEGER NOT NULL,
            data JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )', NEW.model_id);

    EXECUTE format('
        CREATE TABLE model_%s_results (
            id SERIAL PRIMARY KEY,
            model_id INTEGER NOT NULL REFERENCES models(model_id),
            result JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )', NEW.model_id);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER after_model_insert
AFTER INSERT ON models
FOR EACH ROW
EXECUTE FUNCTION create_model_related_tables();


-- CREATE EXAMPLE MODEL 
INSERT INTO models (model_id, name, display_name, description) VALUES (1, 'hello', 'Hello World', 'A simple hello world model');    
INSERT INTO model_binaries (model_id, version, binary_data) VALUES (1, 1, pg_read_binary_file('/docker-entrypoint-initdb.d/binary_testing/hello.o')
);
