-- Subscription plans + per-user price overrides
-- Safe to re-run

CREATE TABLE IF NOT EXISTS subscription_plans (
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) UNIQUE NOT NULL,
    name VARCHAR(80) NOT NULL,
    name_ta VARCHAR(80),
    duration_days INTEGER NOT NULL,
    price_inr INTEGER NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_price_overrides (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id INTEGER NOT NULL REFERENCES subscription_plans(id) ON DELETE CASCADE,
    price_inr INTEGER NOT NULL CHECK (price_inr >= 0),
    note TEXT,
    updated_by VARCHAR(50),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, plan_id)
);

CREATE INDEX IF NOT EXISTS idx_user_price_overrides_user ON user_price_overrides (user_id);

INSERT INTO subscription_plans (code, name, name_ta, duration_days, price_inr, sort_order, is_active)
VALUES
    ('2m', '2 Months', '2 மாதங்கள்', 60, 99, 1, TRUE),
    ('1y', '1 Year', '1 வருடம்', 365, 249, 2, TRUE)
ON CONFLICT (code) DO NOTHING;

UPDATE subscription_plans SET is_active = FALSE WHERE code = '1m';
