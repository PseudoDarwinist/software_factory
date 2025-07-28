-- Manual database fix for pr_number column
-- Run this if the migration doesn't work

-- Add pr_number column to task table if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'task' AND column_name = 'pr_number'
    ) THEN
        ALTER TABLE task ADD COLUMN pr_number INTEGER;
        RAISE NOTICE 'Added pr_number column to task table';
    ELSE
        RAISE NOTICE 'pr_number column already exists';
    END IF;
END $$;

-- Verify the column was added
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'task' AND column_name = 'pr_number';