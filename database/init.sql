-- ==============================================================================
-- PostgreSQL Initialization Script
-- Secure Real-Time Remote Code Execution Laboratory Platform
-- ==============================================================================

-- Ensure cryptographic extension is available for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Database remote_lab_db initialized successfully with pgcrypto and uuid-ossp.';
END $$;
