-- Non-superuser application role so FORCE RLS actually binds.
-- Mounted into docker-entrypoint-initdb.d for fresh volumes;
-- also runnable manually: psql -U urie -d urie -f scripts/init_app_role.sql

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'urie_app') THEN
    CREATE ROLE urie_app LOGIN PASSWORD 'urie' NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END $$;

GRANT CONNECT ON DATABASE urie TO urie_app;
GRANT USAGE, CREATE ON SCHEMA public TO urie_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO urie_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO urie_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO urie_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO urie_app;
