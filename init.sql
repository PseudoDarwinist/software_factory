-- PostgreSQL initialization script
-- This script runs when the PostgreSQL container starts for the first time

-- Create user if not exists (Docker will already create it, but this is a backup)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'sf_user') THEN
        CREATE USER sf_user WITH PASSWORD 'sf_password';
    END IF;
END $$;

-- Grant all privileges to the user
GRANT ALL PRIVILEGES ON DATABASE software_factory TO sf_user;
GRANT ALL ON SCHEMA public TO sf_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO sf_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO sf_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO sf_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO sf_user;