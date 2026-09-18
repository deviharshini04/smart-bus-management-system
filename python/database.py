"""SQLite data access and small, safe migrations for the local prototype."""

from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "smartbus.db"


class ClosingConnection(sqlite3.Connection):
    """Close connections automatically when used in a with statement."""

    def __exit__(self, exc_type, exc_value, traceback):
        result = super().__exit__(exc_type, exc_value, traceback)
        self.close()
        return result


def get_connection(database_path=None):
    database_path = database_path or DATABASE_PATH
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, factory=ClosingConnection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _columns(connection, table):
    return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}


def _add_column(connection, table, name, definition):
    if name not in _columns(connection, table):
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def init_db(database_path=None):
    """Create current tables and migrate the original Phase 1/2 schema safely."""
    with get_connection(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('OWNER', 'CUSTOMER')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS buses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_name TEXT NOT NULL,
                bus_number TEXT NOT NULL UNIQUE,
                bus_name TEXT NOT NULL,
                source TEXT NOT NULL,
                destination TEXT NOT NULL,
                departure_time TEXT NOT NULL,
                arrival_time TEXT NOT NULL,
                total_seats INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_code TEXT NOT NULL UNIQUE,
                bus_id INTEGER NOT NULL,
                passenger_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                seat_number TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bus_id) REFERENCES buses (id)
            );
            CREATE TABLE IF NOT EXISTS booking_seats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER NOT NULL,
                seat_number TEXT NOT NULL,
                FOREIGN KEY (booking_id) REFERENCES bookings (id) ON DELETE CASCADE,
                UNIQUE (booking_id, seat_number)
            );
            """
        )
        _add_column(connection, "buses", "owner_user_id", "INTEGER")
        _add_column(connection, "buses", "lower_deck_seats", "INTEGER")
        _add_column(connection, "buses", "upper_deck_seats", "INTEGER")
        _add_column(connection, "bookings", "customer_user_id", "INTEGER")

        connection.execute("UPDATE buses SET lower_deck_seats = total_seats WHERE lower_deck_seats IS NULL")
        connection.execute("UPDATE buses SET upper_deck_seats = 0 WHERE upper_deck_seats IS NULL")
        # Old records used integer seats. Keep them usable as lower-deck seats.
        connection.execute(
            "UPDATE bookings SET seat_number = 'L' || printf('%02d', seat_number) "
            "WHERE typeof(seat_number) = 'integer'"
        )
        connection.execute(
            """INSERT INTO booking_seats (booking_id, seat_number)
               SELECT bookings.id, bookings.seat_number FROM bookings
               WHERE bookings.seat_number IS NOT NULL
               AND NOT EXISTS (
                   SELECT 1 FROM booking_seats
                   WHERE booking_seats.booking_id = bookings.id
               )"""
        )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS one_active_seat_per_bus "
            "ON bookings (bus_id, seat_number) WHERE status = 'ACTIVE'"
        )


def get_user_by_email(email, database_path=None):
    with get_connection(database_path) as connection:
        return connection.execute("SELECT * FROM users WHERE lower(email) = lower(?)", (email.strip(),)).fetchone()


def get_user(user_id, database_path=None):
    with get_connection(database_path) as connection:
        return connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def insert_user(user, database_path=None):
    with get_connection(database_path) as connection:
        cursor = connection.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (user["name"], user["email"], user["password_hash"], user["role"]),
        )
        return cursor.lastrowid


def get_bus(bus_id, database_path=None):
    with get_connection(database_path) as connection:
        return connection.execute("SELECT * FROM buses WHERE id = ?", (bus_id,)).fetchone()


def get_all_buses(owner_user_id=None, database_path=None):
    with get_connection(database_path) as connection:
        if owner_user_id is None:
            return connection.execute("SELECT * FROM buses ORDER BY id DESC").fetchall()
        return connection.execute(
            "SELECT * FROM buses WHERE owner_user_id = ? ORDER BY id DESC", (owner_user_id,)
        ).fetchall()


def search_buses(source, destination, database_path=None):
    with get_connection(database_path) as connection:
        return connection.execute(
            """SELECT * FROM buses
               WHERE lower(source) = lower(?) AND lower(destination) = lower(?)
               ORDER BY departure_time""",
            (source.strip(), destination.strip()),
        ).fetchall()


def insert_bus(bus, database_path=None):
    with get_connection(database_path) as connection:
        cursor = connection.execute(
            """INSERT INTO buses (
                owner_name, owner_user_id, bus_number, bus_name, source, destination,
                departure_time, arrival_time, total_seats, lower_deck_seats, upper_deck_seats
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                bus["owner_name"], bus.get("owner_user_id"), bus["bus_number"], bus["bus_name"],
                bus["source"], bus["destination"], bus["departure_time"], bus["arrival_time"],
                bus["total_seats"], bus["lower_deck_seats"], bus["upper_deck_seats"],
            ),
        )
        return cursor.lastrowid


def count_active_bookings(bus_id, database_path=None):
    with get_connection(database_path) as connection:
        row = connection.execute(
            """SELECT COUNT(*) AS count FROM booking_seats
               JOIN bookings ON bookings.id = booking_seats.booking_id
               WHERE bookings.bus_id = ? AND bookings.status = 'ACTIVE'""", (bus_id,)
        ).fetchone()
        return row["count"]


def get_bookings_for_bus(bus_id, database_path=None):
    with get_connection(database_path) as connection:
        return connection.execute(
            """SELECT bookings.*, GROUP_CONCAT(booking_seats.seat_number, ', ') AS seat_numbers,
                      COUNT(booking_seats.id) AS seat_count
               FROM bookings LEFT JOIN booking_seats ON booking_seats.booking_id = bookings.id
               WHERE bookings.bus_id = ?
               GROUP BY bookings.id ORDER BY bookings.id DESC""", (bus_id,)
        ).fetchall()


def get_active_seats(bus_id, database_path=None):
    with get_connection(database_path) as connection:
        rows = connection.execute(
            """SELECT booking_seats.seat_number FROM booking_seats
               JOIN bookings ON bookings.id = booking_seats.booking_id
               WHERE bookings.bus_id = ? AND bookings.status = 'ACTIVE'""", (bus_id,)
        ).fetchall()
        return [str(row["seat_number"]) for row in rows]


def count_active_deck_seats(bus_id, prefix, database_path=None):
    with get_connection(database_path) as connection:
        row = connection.execute(
            """SELECT COUNT(*) AS count FROM booking_seats
               JOIN bookings ON bookings.id = booking_seats.booking_id
               WHERE bookings.bus_id = ? AND bookings.status = 'ACTIVE'
               AND booking_seats.seat_number LIKE ?""",
            (bus_id, f"{prefix}%"),
        ).fetchone()
        return row["count"]


def next_booking_number(database_path=None):
    with get_connection(database_path) as connection:
        row = connection.execute("SELECT COUNT(*) AS count FROM bookings").fetchone()
        return 1001 + row["count"]


def insert_booking(booking, database_path=None):
    seat_numbers = list(booking["seat_numbers"])
    if not seat_numbers:
        raise sqlite3.IntegrityError("NO_SEATS")
    with get_connection(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        placeholders = ",".join("?" for _ in seat_numbers)
        taken = connection.execute(
            f"""SELECT booking_seats.seat_number FROM booking_seats
                JOIN bookings ON bookings.id = booking_seats.booking_id
                WHERE bookings.bus_id = ? AND bookings.status = 'ACTIVE'
                AND booking_seats.seat_number IN ({placeholders}) LIMIT 1""",
            (booking["bus_id"], *seat_numbers),
        ).fetchone()
        if taken:
            raise sqlite3.IntegrityError(f"SEAT_TAKEN|{taken['seat_number']}")
        cursor = connection.execute(
            """INSERT INTO bookings
               (booking_code, bus_id, passenger_name, phone, seat_number, customer_user_id, status)
               VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')""",
            (
                booking["booking_code"], booking["bus_id"], booking["passenger_name"],
                booking["phone"], seat_numbers[0], booking.get("customer_user_id"),
            ),
        )
        booking_id = cursor.lastrowid
        connection.executemany(
            "INSERT INTO booking_seats (booking_id, seat_number) VALUES (?, ?)",
            [(booking_id, seat) for seat in seat_numbers],
        )
        return booking_id


def get_booking(booking_code, database_path=None):
    with get_connection(database_path) as connection:
        return connection.execute(
            """SELECT bookings.*, GROUP_CONCAT(booking_seats.seat_number, ', ') AS seat_numbers,
                      COUNT(booking_seats.id) AS seat_count
               FROM bookings LEFT JOIN booking_seats ON booking_seats.booking_id = bookings.id
               WHERE upper(bookings.booking_code) = upper(?)
               GROUP BY bookings.id""", (booking_code.strip(),)
        ).fetchone()


def get_customer_bookings(customer_user_id, database_path=None):
    with get_connection(database_path) as connection:
        return connection.execute(
            """SELECT bookings.*, buses.bus_name, buses.bus_number, buses.source, buses.destination,
                      GROUP_CONCAT(booking_seats.seat_number, ', ') AS seat_numbers,
                      COUNT(booking_seats.id) AS seat_count
               FROM bookings JOIN buses ON buses.id = bookings.bus_id
               LEFT JOIN booking_seats ON booking_seats.booking_id = bookings.id
               WHERE bookings.customer_user_id = ?
               GROUP BY bookings.id ORDER BY bookings.id DESC""",
            (customer_user_id,),
        ).fetchall()


def cancel_booking(booking_code, database_path=None):
    with get_connection(database_path) as connection:
        cursor = connection.execute(
            "UPDATE bookings SET status = 'CANCELLED' WHERE booking_code = ? AND status = 'ACTIVE'",
            (booking_code.strip().upper(),),
        )
        return cursor.rowcount
