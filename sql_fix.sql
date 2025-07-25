-- Fix the stuck iropsagent project
-- Run this in your PostgreSQL database

-- First, let's see the current status
SELECT name, system_map_status, meta_data 
FROM mission_control_project 
WHERE name LIKE '%iropsagent%';

-- Fix the stuck project - since it has no regular project linked, mark as failed
UPDATE mission_control_project 
SET system_map_status = 'failed'
WHERE name LIKE '%iropsagent%' 
AND system_map_status = 'in_progress';

-- Also add the updated_at column if it doesn't exist
ALTER TABLE background_job ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Update existing records
UPDATE background_job SET updated_at = created_at WHERE updated_at IS NULL;

-- Fix any other stuck jobs
UPDATE background_job 
SET status = 'failed', 
    error_message = 'Job timeout - reset by admin',
    completed_at = NOW(),
    updated_at = NOW()
WHERE status IN ('pending', 'running') 
AND created_at < NOW() - INTERVAL '10 minutes';

-- Show final status
SELECT 'Background Jobs:' as summary;
SELECT status, COUNT(*) as count FROM background_job GROUP BY status;

SELECT 'Mission Control Projects:' as summary;
SELECT system_map_status, COUNT(*) as count FROM mission_control_project GROUP BY system_map_status;