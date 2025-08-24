-- Migration to add work order enhancement fields to task table
-- Run this SQL script against your PostgreSQL database

-- Add BACKLOG status to the taskstatus enum
ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'backlog';

-- Add work order enhancement fields to task table
ALTER TABLE task 
ADD COLUMN IF NOT EXISTS enhancement_status VARCHAR(50) DEFAULT 'basic',
ADD COLUMN IF NOT EXISTS implementation_approach TEXT,
ADD COLUMN IF NOT EXISTS implementation_goals JSON,
ADD COLUMN IF NOT EXISTS implementation_strategy TEXT,
ADD COLUMN IF NOT EXISTS technical_dependencies JSON,
ADD COLUMN IF NOT EXISTS files_to_create JSON,
ADD COLUMN IF NOT EXISTS files_to_modify JSON,
ADD COLUMN IF NOT EXISTS blueprint_section_ref VARCHAR(200),
ADD COLUMN IF NOT EXISTS codebase_context JSON,
ADD COLUMN IF NOT EXISTS enhanced_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS enhanced_by VARCHAR(100),
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS approved_by VARCHAR(100);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_task_enhancement_status ON task(enhancement_status);
CREATE INDEX IF NOT EXISTS idx_task_enhanced_at ON task(enhanced_at);

-- Verify the changes
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'task' 
AND column_name IN (
    'enhancement_status', 'implementation_approach', 'implementation_goals',
    'implementation_strategy', 'technical_dependencies', 'files_to_create',
    'files_to_modify', 'blueprint_section_ref', 'codebase_context',
    'enhanced_at', 'enhanced_by', 'approved_at', 'approved_by'
)
ORDER BY column_name;