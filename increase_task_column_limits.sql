-- Migration to increase column limits for Task model fields
-- This prevents "value too long for type character varying(200)" errors

-- Increase goal_line from 200 to 1000 characters
ALTER TABLE task ALTER COLUMN goal_line TYPE VARCHAR(1000);

-- Increase blueprint_section_ref from 200 to 1000 characters  
ALTER TABLE task ALTER COLUMN blueprint_section_ref TYPE VARCHAR(1000);

-- Increase branch_name from 200 to 500 characters (for longer branch names)
ALTER TABLE task ALTER COLUMN branch_name TYPE VARCHAR(500);

-- Add index on commonly queried fields if not exists
CREATE INDEX IF NOT EXISTS idx_task_spec_id_status ON task(spec_id, status);
CREATE INDEX IF NOT EXISTS idx_task_project_id_status ON task(project_id, status);