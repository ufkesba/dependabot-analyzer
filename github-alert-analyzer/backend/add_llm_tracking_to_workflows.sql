-- Add LLM tracking columns to analysis_workflows table
ALTER TABLE analysis_workflows 
ADD COLUMN IF NOT EXISTS llm_provider VARCHAR(50),
ADD COLUMN IF NOT EXISTS llm_model VARCHAR(100);
