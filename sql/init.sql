CREATE DATABASE civic_db;

GRANT ALL ON DATABASE civic_db TO civic_db_admin;

\connect civic_db;

-- SET TIMEZONE (America/New_York)

ALTER DATABASE civic_db SET timezone TO 'UTC';

