CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  goal TEXT NOT NULL,
  status TEXT NOT NULL,
  plan_json TEXT,
  steps_json TEXT,
  summary TEXT,
  started_at INTEGER,
  ended_at INTEGER
);

CREATE TABLE IF NOT EXISTS macros (
  id TEXT PRIMARY KEY,
  goal_pattern TEXT NOT NULL,
  steps_json TEXT NOT NULL,
  success_count INTEGER DEFAULT 0,
  created_at INTEGER,
  last_used_at INTEGER
);

CREATE VIRTUAL TABLE IF NOT EXISTS macros_fts USING fts5(goal_pattern, content=macros);
