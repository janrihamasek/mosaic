CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    activity TEXT NOT NULL,
    description TEXT,
    value REAL,
    note TEXT,
    activity_category TEXT NOT NULL DEFAULT '',
    activity_goal REAL NOT NULL DEFAULT 0,
    UNIQUE(date, activity)
);
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL DEFAULT '',
    goal REAL NOT NULL DEFAULT 0,
    description TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    frequency_per_day INTEGER NOT NULL DEFAULT 1,
    frequency_per_week INTEGER NOT NULL DEFAULT 1,
    deactivated_at TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS backup_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    enabled INTEGER NOT NULL DEFAULT 0,
    interval_minutes INTEGER NOT NULL DEFAULT 60,
    last_run TEXT
);

CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(date);
CREATE INDEX IF NOT EXISTS idx_entries_activity ON entries(activity);
CREATE INDEX IF NOT EXISTS idx_entries_activity_category ON entries(activity_category);
CREATE INDEX IF NOT EXISTS idx_activities_category ON activities(category);
