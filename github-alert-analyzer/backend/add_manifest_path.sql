-- Migration: Add manifest_path column to alerts table
-- Date: 2025-12-08
-- Description: Add manifest_path field to track the impacted manifest file for each alert

-- Add manifest_path column
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS manifest_path VARCHAR(500);

-- Add comment for documentation
COMMENT ON COLUMN alerts.manifest_path IS 'Path to the manifest file (package.json, requirements.txt, Gemfile, etc.) affected by this alert';

-- No need to backfill - existing alerts will have NULL manifest_path until next sync
