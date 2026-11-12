-- Run once in Supabase SQL Editor before deploying collector 0.4.
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS matched_skills jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS missing_skills jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS required_skills jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS study_recommendations jsonb NOT NULL DEFAULT '[]'::jsonb;
-- Existing jobs are preserved; new analysis fields populate on next ingestion.
