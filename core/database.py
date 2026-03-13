import sqlite3
from typing import List, Dict
from pathlib import Path

DB_URI = "sqlite:///data/theatre_agenda.db"


# -------------------- DB HELPERS --------------------

def _sqlite_path(db_uri: str) -> str:
    """Extract file path from SQLite URI"""
    assert db_uri.startswith("sqlite:///")
    return db_uri.replace("sqlite:///", "", 1)


def _open(db_uri: str) -> sqlite3.Connection:
    """Open SQLite connection with foreign keys enabled"""
    path = _sqlite_path(db_uri)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON;")
    return con


# -------------------- SCHEMA INITIALIZATION --------------------

def init_db(db_uri: str = DB_URI):
    """Initialize database with theatres and shows tables"""
    with _open(db_uri) as con:
        # Create theatres table
        con.execute("""
            CREATE TABLE IF NOT EXISTS theatres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                data_source TEXT CHECK(data_source IN ('scrape','csv')) NOT NULL,
                active INTEGER DEFAULT 1,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_scraped_at DATETIME
            );
        """)

        # Create shows table
        con.execute("""
            CREATE TABLE IF NOT EXISTS shows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                theatre_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                type TEXT,
                date TEXT,
                time TEXT,
                description TEXT,
                url TEXT,
                scraped_at DATETIME,
                hash TEXT,
                status TEXT DEFAULT 'active',
                FOREIGN KEY (theatre_id) REFERENCES theatres(id)
            );
        """)

        con.commit()


# -------------------- THEATRE CRUD OPERATIONS --------------------

def add_theatre(name: str, url: str, data_source: str, db_uri: str = DB_URI):
    """Add new theatre to the database"""
    with _open(db_uri) as con:
        con.execute("""
            INSERT INTO theatres (name, url, data_source)
            VALUES (?, ?, ?);
        """, (name, url, data_source))
        con.commit()


def get_theatres(active_only: bool = True, db_uri: str = DB_URI) -> List[Dict]:
    """Get all theatres from the database

    Args:
        active_only: If True, only return theatres where active=1
        db_uri: Database URI

    Returns:
        List of theatre dictionaries
    """
    with _open(db_uri) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        if active_only:
            cur.execute("SELECT * FROM theatres WHERE active = 1;")
        else:
            cur.execute("SELECT * FROM theatres;")

        return [dict(row) for row in cur.fetchall()]


def update_theatre(theatre_id: int, db_uri: str = DB_URI, **fields):
    """Update theatre with the given id and fields

    Args:
        theatre_id: ID of theatre to update
        db_uri: Database URI
        **fields: Keyword arguments of fields to update (e.g., name='New Name')
    """
    with _open(db_uri) as con:
        set_clause = ", ".join([f"{key} = ?" for key in fields.keys()])
        values = list(fields.values()) + [theatre_id]

        con.execute(f"""
            UPDATE theatres
            SET {set_clause}
            WHERE id = ?;
        """, values)
        con.commit()


def deactivate_theatre(theatre_id: int, db_uri: str = DB_URI):
    """Set theatre active status to 0 (inactive)

    Args:
        theatre_id: ID of theatre to deactivate
        db_uri: Database URI
    """
    with _open(db_uri) as con:
        con.execute("""
            UPDATE theatres
            SET active = 0
            WHERE id = ?;
        """, (theatre_id,))
        con.commit()


# -------------------- SHOW CRUD OPERATIONS --------------------

def save_shows(theatre_id: int, shows_list: List[Dict], db_uri: str = DB_URI):
    """Save list of shows to the database

    Args:
        theatre_id: ID of the theatre these shows belong to
        shows_list: List of show dictionaries with keys: title, type, date, time,
                    description, url, scraped_at, hash
        db_uri: Database URI
    """
    with _open(db_uri) as con:
        for show in shows_list:
            con.execute("""
                INSERT INTO shows (theatre_id, title, type, date, time, description, url, scraped_at, hash, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active');
            """, (
                theatre_id,
                show['title'],
                show.get('type'),
                show.get('date'),
                show.get('time'),
                show.get('description'),
                show.get('url'),
                show.get('scraped_at'),
                show['hash']
            ))
        con.commit()


def get_shows_by_theatre(theatre_id: int, active_only: bool = True, db_uri: str = DB_URI) -> List[Dict]:
    """Get shows for a specific theatre

    Args:
        theatre_id: ID of the theatre
        active_only: If True, only return shows where status='active'
        db_uri: Database URI

    Returns:
        List of show dictionaries
    """
    with _open(db_uri) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        if active_only:
            cur.execute("""
                SELECT * FROM shows
                WHERE theatre_id = ? AND status = 'active';
            """, (theatre_id,))
        else:
            cur.execute("""
                SELECT * FROM shows
                WHERE theatre_id = ?;
            """, (theatre_id,))

        return [dict(row) for row in cur.fetchall()]


def get_last_scraped_at(theatre_id: int, db_uri: str = DB_URI) -> str:
    """Return timestamp of most recent scrape for a theatre"""
    with _open(db_uri) as con:
        cur = con.cursor()
        cur.execute("""
            SELECT MAX(scraped_at) FROM shows
            WHERE theatre_id = ?
        """, (theatre_id,))
        row = cur.fetchone()
        return row[0] if row else None
