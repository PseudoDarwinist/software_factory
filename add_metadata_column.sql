-- Add job_metadata column to background_job table
-- This adds the JSON job_metadata field needed for async spec generation
-- (renamed from 'metadata' to avoid SQLAlchemy reserved word conflict)

ALTER TABLE background_job ADD COLUMN job_metadata JSON;

-- Update any existing spec_generation jobs to have empty job_metadata
UPDATE background_job SET job_metadata = '{}' WHERE job_type = 'spec_generation' AND job_metadata IS NULL;