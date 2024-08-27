import sqlite3


def set_up_chat_history_backend_table(conn: sqlite3.Connection):
    with open("mapchat/backends/chat_history_schema.sql", "r") as schema_file:
        schema = schema_file.read()
    cursor = conn.cursor()
    cursor.executescript(schema)
    conn.commit()


def tear_down_chat_history_backend_table(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.executescript("""DROP TABLE chat""")
    conn.commit()


def set_up_location_history_backend_table(conn: sqlite3.Connection):
    with open("mapchat/backends/location_history_schema.sql",
              "r") as schema_file:
        schema = schema_file.read()
    cursor = conn.cursor()
    cursor.executescript(schema)
    conn.commit()


def tear_down_location_history_backend_table(conn: sqlite3.Connection):
    with open("mapchat/backends/drop_location_history_tables.sql",
              "r") as drop_tables_file:
        drop_tables_script = drop_tables_file.read()
    cursor = conn.cursor()
    cursor.executescript(drop_tables_script)
