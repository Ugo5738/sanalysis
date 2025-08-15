-- Supabase schema for Image Condition Analysis microservice
-- Safe to run multiple times (IF NOT EXISTS used). Adjust names if your app label differs from 'analysis'.

-- Extensions (optional)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==============
-- Core tables
-- ==============

CREATE TABLE IF NOT EXISTS analysis_prompt (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  content TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analysis_property (
  id BIGSERIAL PRIMARY KEY,
  super_id VARCHAR(1028),
  bedrooms INTEGER,
  bathrooms INTEGER,
  floorplan_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
  failed_downloads JSONB NOT NULL DEFAULT '[]'::jsonb,
  image_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analysis_propertyimage (
  id BIGSERIAL PRIMARY KEY,
  property_id BIGINT NOT NULL REFERENCES analysis_property(id) ON DELETE CASCADE,
  image VARCHAR(255) NOT NULL,
  original_url VARCHAR(200) NOT NULL,
  main_category VARCHAR(100) NOT NULL,
  sub_category VARCHAR(100) NOT NULL,
  room_type VARCHAR(100) NOT NULL DEFAULT '',
  condition_label VARCHAR(100) NOT NULL DEFAULT '',
  condition_score INTEGER,
  reasoning TEXT NOT NULL DEFAULT '',
  embedding JSONB,
  similarity_scores JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analysis_groupedimages (
  id BIGSERIAL PRIMARY KEY,
  property_id BIGINT NOT NULL REFERENCES analysis_property(id) ON DELETE CASCADE,
  main_category VARCHAR(100) NOT NULL,
  sub_category VARCHAR(100) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT analysis_groupedimages_unique UNIQUE (property_id, main_category, sub_category)
);

CREATE TABLE IF NOT EXISTS analysis_groupedimages_images (
  id BIGSERIAL PRIMARY KEY,
  groupedimages_id BIGINT NOT NULL REFERENCES analysis_groupedimages(id) ON DELETE CASCADE,
  propertyimage_id BIGINT NOT NULL REFERENCES analysis_propertyimage(id) ON DELETE CASCADE,
  CONSTRAINT analysis_groupedimages_images_unique UNIQUE (groupedimages_id, propertyimage_id)
);

CREATE TABLE IF NOT EXISTS analysis_mergedpropertyimage (
  id BIGSERIAL PRIMARY KEY,
  property_id BIGINT NOT NULL REFERENCES analysis_property(id) ON DELETE CASCADE,
  image VARCHAR(255) NOT NULL,
  main_category VARCHAR(100) NOT NULL,
  sub_category VARCHAR(100) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analysis_mergedpropertyimage_images (
  id BIGSERIAL PRIMARY KEY,
  mergedpropertyimage_id BIGINT NOT NULL REFERENCES analysis_mergedpropertyimage(id) ON DELETE CASCADE,
  propertyimage_id BIGINT NOT NULL REFERENCES analysis_propertyimage(id) ON DELETE CASCADE,
  CONSTRAINT analysis_mergedpropertyimage_images_unique UNIQUE (mergedpropertyimage_id, propertyimage_id)
);

CREATE TABLE IF NOT EXISTS analysis_sampleimage (
  id BIGSERIAL PRIMARY KEY,
  category VARCHAR(100) NOT NULL,
  subcategory VARCHAR(100) NOT NULL,
  condition VARCHAR(100) NOT NULL,
  image VARCHAR(255) NOT NULL,
  image_hash CHAR(32) UNIQUE NOT NULL,
  embedding JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analysis_mergedsampleimage (
  id BIGSERIAL PRIMARY KEY,
  category VARCHAR(100) NOT NULL,
  subcategory VARCHAR(100) NOT NULL,
  condition VARCHAR(100) NOT NULL,
  image VARCHAR(255) NOT NULL,
  quadrant_mapping JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ==============
-- Analysis tables
-- ==============

CREATE TABLE IF NOT EXISTS image_condition_analysis (
  id BIGSERIAL PRIMARY KEY,
  super_id VARCHAR(1028),
  image_url VARCHAR(200),
  image_id INTEGER NOT NULL,
  main_category VARCHAR(100),
  image_room_name VARCHAR(100),
  image_room_type VARCHAR(100),
  image_group_number INTEGER,
  merged_image_number INTEGER,
  merged_image_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
  similarity_image_excellent DOUBLE PRECISION,
  similarity_image_above_average DOUBLE PRECISION,
  similarity_image_below_average DOUBLE PRECISION,
  similarity_image_poor DOUBLE PRECISION,
  image_condition_score INTEGER,
  image_condition_label VARCHAR(50),
  image_condition_explanation TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_image_condition_analysis_super_image ON image_condition_analysis(super_id, image_id);

CREATE TABLE IF NOT EXISTS overall_image_analysis (
  id BIGSERIAL PRIMARY KEY,
  super_id VARCHAR(1028),
  property_url VARCHAR(200),
  total_images_processed INTEGER,
  distribution_images_excellent DOUBLE PRECISION,
  distribution_images_above_average DOUBLE PRECISION,
  distribution_images_below_average DOUBLE PRECISION,
  distribution_images_poor DOUBLE PRECISION,
  overall_condition_score DOUBLE PRECISION,
  overall_condition_label VARCHAR(50),
  images_of_concern INTEGER,
  number_of_bedrooms INTEGER,
  condition_confidence_beds VARCHAR(20),
  condition_explanation TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analysis_analysistask (
  id BIGSERIAL PRIMARY KEY,
  super_id VARCHAR(100) UNIQUE,
  status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
  progress DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  stage VARCHAR(50) NOT NULL DEFAULT '',
  stage_progress JSONB NOT NULL DEFAULT '{}'::jsonb,
  notes JSONB NOT NULL DEFAULT '{}'::jsonb,
  trigger_analysis BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analysis_event (
  id BIGSERIAL PRIMARY KEY,
  super_id VARCHAR(1028) NOT NULL,
  event_type VARCHAR(32) NOT NULL,
  source VARCHAR(128) NOT NULL DEFAULT 'image_condition_service',
  target VARCHAR(256),
  endpoint VARCHAR(512),
  method VARCHAR(16),
  http_status INTEGER,
  error_code VARCHAR(128),
  error_message TEXT,
  request_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  response_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  response_count INTEGER,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_event_superid_created ON analysis_event(super_id, created_at);
