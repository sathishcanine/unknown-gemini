-- Admin analytics foundation migration
-- Safe to re-run: uses IF NOT EXISTS / ON CONFLICT guards where possible

-- 1. User device/geo/activity metadata
ALTER TABLE users ADD COLUMN IF NOT EXISTS platform VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS os_version VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS app_version VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS country VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP;

-- Backfill last_active_at from most recent activity so existing users aren't all "never active"
UPDATE users u
SET last_active_at = sub.max_ts
FROM (
    SELECT user_id, MAX(timestamp) AS max_ts FROM activity_logs GROUP BY user_id
) sub
WHERE u.id = sub.user_id AND u.last_active_at IS NULL;

-- 2. Per-question response time (nullable; only populated going forward)
ALTER TABLE user_answers ADD COLUMN IF NOT EXISTS response_time_ms INTEGER;

-- 3. Dedicated admin users table (separate from app users / Google Sign-In)
CREATE TABLE IF NOT EXISTS admin_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

-- 4. Helpful indexes for analytics queries over time ranges
CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs (timestamp);
CREATE INDEX IF NOT EXISTS idx_activity_logs_user_event ON activity_logs (user_id, event_type);
CREATE INDEX IF NOT EXISTS idx_test_sessions_timestamp ON test_sessions (timestamp);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users (created_at);
CREATE INDEX IF NOT EXISTS idx_users_last_active_at ON users (last_active_at);
