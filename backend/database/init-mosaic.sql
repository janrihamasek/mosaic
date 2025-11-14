\set devdb mosaic_dev
\set proddb mosaic_prod
\set stagingdb mosaic_staging

SELECT 'CREATE DATABASE ' || quote_ident(:'devdb') || ' OWNER mosaic;'
WHERE NOT EXISTS (
    SELECT 1 FROM pg_database WHERE datname = :'devdb'
)\gexec

SELECT 'CREATE DATABASE ' || quote_ident(:'proddb') || ' OWNER mosaic;'
WHERE NOT EXISTS (
    SELECT 1 FROM pg_database WHERE datname = :'proddb'
)\gexec

SELECT 'CREATE DATABASE ' || quote_ident(:'stagingdb') || ' OWNER mosaic;'
WHERE NOT EXISTS (
    SELECT 1 FROM pg_database WHERE datname = :'stagingdb'
)\gexec
