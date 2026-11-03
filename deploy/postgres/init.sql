-- mytube PostgreSQL initialisation script
-- Automatically executed on first container volume initialization

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
