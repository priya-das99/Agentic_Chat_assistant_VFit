-- Migration: Add meal tracking support
-- This allows users to log meals with calorie information

CREATE TABLE IF NOT EXISTS meal_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    meal_type VARCHAR(50) NOT NULL,  -- breakfast, lunch, dinner, snack
    meal_name VARCHAR(200),
    calories INTEGER NOT NULL,
    protein_grams INTEGER,
    carbs_grams INTEGER,
    fat_grams INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE INDEX IF NOT EXISTS idx_meal_logs_user_id ON meal_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_meal_logs_created_at ON meal_logs(created_at);
