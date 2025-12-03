CREATE TABLE IF NOT EXISTS entries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date VARCHAR(10) NOT NULL,
    activity VARCHAR(120) NOT NULL,
    description TEXT,
    value DOUBLE PRECISION DEFAULT 0,
    note TEXT,
    activity_category VARCHAR(120) NOT NULL DEFAULT '',
    activity_goal DOUBLE PRECISION NOT NULL DEFAULT 0,
    activity_type VARCHAR(16) NOT NULL DEFAULT 'positive',
    UNIQUE (user_id, date, activity)
);

CREATE TABLE IF NOT EXISTS activities (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    category VARCHAR(120) NOT NULL DEFAULT '',
    goal DOUBLE PRECISION NOT NULL DEFAULT 0,
    description TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    frequency_per_day INTEGER NOT NULL DEFAULT 1,
    frequency_per_week INTEGER NOT NULL DEFAULT 1,
    deactivated_at VARCHAR(32),
    activity_type VARCHAR(16) NOT NULL DEFAULT 'positive',
    is_system BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (user_id, name)
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS backup_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    interval_minutes INTEGER NOT NULL DEFAULT 60,
    last_run TIMESTAMPTZ,
    UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_entries_user_id_date ON entries(user_id, date);
CREATE INDEX IF NOT EXISTS idx_entries_user_id_activity ON entries(user_id, activity);
CREATE INDEX IF NOT EXISTS idx_entries_user_id_activity_category ON entries(user_id, activity_category);
CREATE INDEX IF NOT EXISTS idx_activities_user_id ON activities(user_id);
CREATE INDEX IF NOT EXISTS idx_activities_user_category ON activities(user_id, category);
