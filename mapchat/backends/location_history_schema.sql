-- Initialize the database.
-- Drop any existing data and create empty tables.

DROP TABLE IF EXISTS visit;
DROP TABLE IF EXISTS raw_place;

CREATE TABLE visit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  start_time INTEGER NOT NULL,
  end_time INTEGER NOT NULL,
  place_id TEXT NOT NULL,
  semantic_type TEXT
    CHECK( semantic_type IN
      ('UNKNOWN', 'HOME', 'WORK', 'INFERRED_HOME', 'INFERRED_WORK', 'SEARCHED_ADDRESS'))
      NOT NULL DEFAULT 'UNKNOWN'
);

CREATE TABLE raw_place (
  place_id TEXT PRIMARY KEY,
  place_info TEXT NOT NULL
);