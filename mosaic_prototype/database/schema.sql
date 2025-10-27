CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    activity TEXT NOT NULL,
    description TEXT,
    value REAL,
    note TEXT,
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
    frequency_per_week INTEGER NOT NULL DEFAULT 1
);
