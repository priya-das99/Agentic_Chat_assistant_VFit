-- Migration: Add fitness metrics to activity_logs and gender to user_profiles
-- Run this to add calorie and step tracking

-- Add fitness metrics to activity_logs
ALTER TABLE activity_logs ADD COLUMN calories_burned INTEGER;
ALTER TABLE activity_logs ADD COLUMN steps_count INTEGER;
ALTER TABLE activity_logs ADD COLUMN intensity_level VARCHAR(20);

-- Add gender to user_profiles for BMR calculation
ALTER TABLE user_profiles ADD COLUMN gender VARCHAR(10);
