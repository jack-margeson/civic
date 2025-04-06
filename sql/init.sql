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

CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    client_uuid UUID UNIQUE DEFAULT gen_random_uuid(),
    ip VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    status INTEGER NOT NULL DEFAULT 0, -- 0: inactive, 1: active
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE FUNCTION update_last_connected_at() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 1 THEN
        NEW.last_connected_at = CURRENT_TIMESTAMP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER before_client_update
BEFORE UPDATE ON clients
FOR EACH ROW
WHEN (OLD.status IS DISTINCT FROM NEW.status)
EXECUTE FUNCTION update_last_connected_at();

CREATE OR REPLACE FUNCTION create_model_related_tables() RETURNS TRIGGER AS $$
BEGIN
    EXECUTE format('
        CREATE TABLE model_%s_data (
            id SERIAL PRIMARY KEY,
            model_id INTEGER NOT NULL REFERENCES models(model_id),
            data JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )', NEW.model_id);

    EXECUTE format('
        CREATE TABLE model_%s_results (
            id SERIAL PRIMARY KEY,
            data_split_id INTEGER NOT NULL REFERENCES model_%1$s_data(id),
            model_id INTEGER NOT NULL REFERENCES models(model_id),
            client_uuid UUID NOT NULL REFERENCES clients(client_uuid),
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


-- CREATE EXAMPLE MODEL HELLO WORLD

-- INSERT INTO models (model_id, name, display_name, description) VALUES (1, 'hello', 'Hello World', 'A simple hello world executable');    
-- INSERT INTO model_binaries (model_id, version, binary_data) VALUES (1, 1, pg_read_binary_file('/docker-entrypoint-initdb.d/binary_testing/hello.o')
-- );

-- CREATE EXAMPLE MODEL ALPHABET

INSERT INTO models (model_id, name, display_name, description) VALUES (1, 'alphabet', 'Alphabet', 'Alphabet testing program');
INSERT INTO model_binaries (model_id, version, binary_data) VALUES (1, 1, pg_read_binary_file('/docker-entrypoint-initdb.d/models/alphabet.o')
);
