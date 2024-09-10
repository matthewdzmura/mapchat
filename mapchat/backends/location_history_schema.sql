-- Initialize the database.
-- Drop any existing data and create empty tables.

CREATE TABLE IF NOT EXISTS visit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  start_time_iso1806 TEXT NOT NULL,
  end_time_iso1806 TEXT NOT NULL,
  place_id TEXT NOT NULL,
  semantic_type TEXT
    CHECK( semantic_type IN
      ('UNKNOWN', 'HOME', 'WORK', 'INFERRED_HOME', 'INFERRED_WORK', 'SEARCHED_ADDRESS'))
      NOT NULL DEFAULT 'UNKNOWN'
);

CREATE TABLE IF NOT EXISTS raw_place (
  place_id TEXT PRIMARY KEY,
  place_info TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS places (
    place_id TEXT PRIMARY KEY,
    name TEXT,
    -- When querying for specific pieces of the address, prefer the address_components table
    -- instead of formatted_address.
    formatted_address TEXT,
    formatted_phone_number TEXT,
    international_phone_number TEXT,
    business_status TEXT,
    curbside_pickup BOOLEAN,
    delivery BOOLEAN,
    dine_in BOOLEAN,
    reservable BOOLEAN,
    serves_beer BOOLEAN,
    serves_brunch BOOLEAN,
    serves_dinner BOOLEAN,
    serves_lunch BOOLEAN,
    serves_vegetarian_food BOOLEAN,
    serves_wine BOOLEAN,
    takeout BOOLEAN,
    price_level INTEGER,
    rating REAL,
    user_ratings_total INTEGER,
    url TEXT,
    website TEXT,
    wheelchair_accessible_entrance BOOLEAN,
    utc_offset INTEGER,
    vicinity TEXT,
    icon TEXT,
    icon_background_color TEXT,
    icon_mask_base_uri TEXT,
    editorial_summary_language TEXT,
    editorial_summary_overview TEXT,
    geometry_location_lat REAL,
    geometry_location_lng REAL,
    geometry_viewport_northeast_lat REAL,
    geometry_viewport_northeast_lng REAL,
    geometry_viewport_southwest_lat REAL,
    geometry_viewport_southwest_lng REAL,
    categories TEXT
);

-- This is the best way to find out fine-grained details about where a place is
-- located. Example query to name every place visited in California:
-- SELECT p.name FROM places p
-- JOIN address_components ac ON p.place_id = ac.place_id
-- WHERE ac.types LIKE '%administrative_area_level_1%' AND ac.long_name = 'California';
CREATE TABLE IF NOT EXISTS address_components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id TEXT,
    long_name TEXT,
    short_name TEXT,
    -- types is a repeated field that can include the following values:
    -- street_number: The precise street number in the address e.g. 123 in 123 Main Street.
    -- route: The street name e.g. Main Street in 123 Main Street
    -- sublocality: A sublocality is a subdivision within a locality e.g. a neighborhood/borough like Manhattan
    -- locality: The locality corresponds to the city/town e.g. New York City
    -- administrative_area_level_2: The second administrative level e.g. a county like New York County
    -- administrative_area_level_1: The first administrative level e.g. a state like New York
    -- country: The country in which the place is located e.g. United States
    -- postal_code: The postal code of the place e.g. 10011
    types TEXT,
    FOREIGN KEY(place_id) REFERENCES places(place_id)
);

CREATE TABLE IF NOT EXISTS opening_hours (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id TEXT,
    open_now BOOLEAN,
    FOREIGN KEY(place_id) REFERENCES places(place_id)
);

CREATE TABLE IF NOT EXISTS opening_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opening_hours_id INTEGER,
    open_day INTEGER,
    open_time TEXT,
    close_day INTEGER,
    close_time TEXT,
    FOREIGN KEY(opening_hours_id) REFERENCES opening_hours(id)
);

CREATE TABLE IF NOT EXISTS special_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opening_hours_id INTEGER,
    date TEXT,
    exceptional_hours BOOLEAN,
    FOREIGN KEY(opening_hours_id) REFERENCES opening_hours(id)
);

CREATE TABLE IF NOT EXISTS secondary_opening_hours (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id TEXT,
    type TEXT,
    open_now BOOLEAN,
    FOREIGN KEY(place_id) REFERENCES places(place_id)
);

CREATE TABLE IF NOT EXISTS secondary_opening_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    secondary_opening_hours_id INTEGER,
    open_day INTEGER,
    open_time TEXT,
    close_day INTEGER,
    close_time TEXT,
    open_date TEXT,
    close_date TEXT,
    FOREIGN KEY(secondary_opening_hours_id) REFERENCES secondary_opening_hours(id)
);

CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id TEXT,
    height INTEGER,
    width INTEGER,
    photo_reference TEXT,
    html_attributions TEXT,
    FOREIGN KEY(place_id) REFERENCES places(place_id)
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id TEXT,
    author_name TEXT,
    author_url TEXT,
    language TEXT,
    original_language TEXT,
    profile_photo_url TEXT,
    rating INTEGER,
    relative_time_description TEXT,
    text TEXT,
    time INTEGER,
    translated BOOLEAN,
    FOREIGN KEY(place_id) REFERENCES places(place_id)
);