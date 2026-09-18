"""Isolated authentication, multi-seat booking, and ownership tests."""

import sys
import tempfile
import unittest
from pathlib import Path
from werkzeug.datastructures import MultiDict

PYTHON_DIR = Path(__file__).resolve().parents[1] / "python"
sys.path.insert(0, str(PYTHON_DIR))

import database  # noqa: E402
import java_bridge  # noqa: E402
from app import app  # noqa: E402


class SmartBusBlock10Tests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database.DATABASE_PATH = Path(self.temp_dir.name) / "test-smartbus.db"
        database.init_db()
        self.client = app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def signup(self, name, email, role):
        return self.client.post("/signup", data={
            "name": name, "email": email, "password": "demo123",
            "confirm_password": "demo123", "role": role,
        })

    def signin(self, email):
        return self.client.post("/signin", data={"email": email, "password": "demo123"})

    def register_demo_bus(self):
        return self.client.post("/owner/register", data={
            "bus_name": "Green Line", "bus_number": "TN-45-AB-1234",
            "source": "Trichy", "destination": "Chennai", "departure_time": "08:00",
            "arrival_time": "13:00", "lower_deck_seats": "20", "upper_deck_seats": "20",
        })

    def prepare_customer_with_bus(self):
        self.signup("Owner One", "one@test.local", "OWNER")
        self.signin("one@test.local")
        self.register_demo_bus()
        self.client.post("/logout")
        self.signup("Anu", "anu@test.local", "CUSTOMER")
        self.signin("anu@test.local")

    def book(self, seats, passenger="Anu"):
        return self.client.post("/customer/bus/1/book", data=MultiDict([
            ("seat_count", str(len(seats))),
            *[("seat_number", seat) for seat in seats],
            ("passenger_name", passenger), ("phone", "9876543210"),
        ]))

    def test_authentication_and_role_protection(self):
        self.assertEqual(self.signup("ABC Travels", "owner@smartbus.local", "OWNER").status_code, 302)
        self.assertIn(b"already exists", self.signup("Second", "OWNER@smartbus.local", "OWNER").data)
        self.assertEqual(self.signin("owner@smartbus.local").status_code, 302)
        self.client.post("/logout")
        self.signup("Anu", "anu@test.local", "CUSTOMER")
        self.signin("anu@test.local")
        owner_page = self.client.get("/owner/dashboard")
        self.assertEqual(owner_page.status_code, 302)
        self.assertIn(b"not available", self.client.get(owner_page.location).data)
        self.client.post("/logout")
        self.assertIn(b"Please sign in", self.client.get("/customer", follow_redirects=True).data)

    def test_quantity_page_and_invalid_quantity_requests(self):
        self.prepare_customer_with_bus()
        quantity = self.client.get("/customer/bus/1/seats")
        self.assertIn(b"How many seats", quantity.data)
        invalid_zero = self.client.post("/customer/bus/1/choose-seats", data={"seat_count": "0"})
        self.assertIn(b"between 1 and 6", invalid_zero.data)
        invalid_seven = self.client.post("/customer/bus/1/choose-seats", data={"seat_count": "7"})
        self.assertIn(b"between 1 and 6", invalid_seven.data)
        invalid_negative = self.client.post("/customer/bus/1/choose-seats", data={"seat_count": "-1"})
        self.assertIn(b"between 1 and 6", invalid_negative.data)
        invalid_text = self.client.post("/customer/bus/1/choose-seats", data={"seat_count": "many"})
        self.assertIn(b"between 1 and 6", invalid_text.data)

    def test_one_two_and_six_seat_bookings(self):
        self.prepare_customer_with_bus()
        self.assertEqual(self.book(["L01"]).status_code, 302)
        self.assertEqual(database.get_active_seats(1), ["L01"])
        self.client.post("/customer/cancel", data={"booking_code": "BK1001"})
        self.assertEqual(self.book(["L02", "U01"]).status_code, 302)
        self.client.post("/customer/cancel", data={"booking_code": "BK1002"})
        six_seats = ["L05", "L06", "L07", "U11", "U12", "U14"]
        response = self.book(six_seats)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(set(database.get_active_seats(1)), set(six_seats))
        confirmation = self.client.get(response.location)
        for seat in six_seats:
            self.assertIn(seat.encode(), confirmation.data)
        self.assertIn(b"Total Seats Booked", confirmation.data)

    def test_fewer_and_more_than_requested_are_rejected(self):
        self.prepare_customer_with_bus()
        fewer = self.client.post("/customer/bus/1/book", data=MultiDict([
            ("seat_count", "3"), ("seat_number", "L01"), ("seat_number", "L02"),
            ("passenger_name", "Anu"), ("phone", "9876543210"),
        ]))
        self.assertIn(b"exactly 3 seats", fewer.data)
        more = self.client.post("/customer/bus/1/book", data=MultiDict([
            ("seat_count", "2"), ("seat_number", "L01"), ("seat_number", "L02"), ("seat_number", "U01"),
            ("passenger_name", "Anu"), ("phone", "9876543210"),
        ]))
        self.assertIn(b"exactly 2 seats", more.data)
        self.assertEqual(database.get_active_seats(1), [])

    def test_mixed_deck_validation_and_all_or_nothing(self):
        self.prepare_customer_with_bus()
        self.assertEqual(java_bridge.available_count(20, 20, []), 40)
        self.assertEqual(java_bridge.check_seat(20, 20, [], "L01"), "AVAILABLE")
        with self.assertRaises(ValueError):
            java_bridge.check_seat(20, 0, [], "U01")
        with self.assertRaises(ValueError):
            java_bridge.validate_booking(20, 20, ["U01"], ["L01", "U01"], "Anu", "9876543210")
        invalid = self.book(["L01", "U99"])
        self.assertIn(b"U99 is invalid", invalid.data)
        rejected = self.client.post("/customer/bus/1/book", data=MultiDict([
            ("seat_count", "2"), ("seat_number", "L01"), ("seat_number", "U01"),
            ("passenger_name", "Anu"), ("phone", "9876543210"),
        ]))
        # U01 is not booked yet, so this request succeeds; book it, then retry atomically.
        self.assertEqual(rejected.status_code, 302)
        self.client.post("/customer/cancel", data={"booking_code": "BK1001"})
        self.book(["U01"])
        rejected = self.client.post("/customer/bus/1/book", data=MultiDict([
            ("seat_count", "2"), ("seat_number", "L01"), ("seat_number", "U01"),
            ("passenger_name", "Anu"), ("phone", "9876543210"),
        ]))
        self.assertIn(b"U01 is no longer available", rejected.data)
        self.assertEqual(database.get_active_seats(1), ["U01"])

    def test_owner_counts_history_and_full_cancellation(self):
        self.prepare_customer_with_bus()
        self.book(["L05", "L06", "U14"])
        self.assertEqual(database.count_active_bookings(1), 3)
        self.assertEqual(database.get_customer_bookings(2)[0]["seat_count"], 3)
        self.client.post("/logout")
        self.signin("one@test.local")
        self.assertIn(b"<strong>3</strong>", self.client.get("/owner/dashboard").data)
        self.client.post("/logout")
        self.signin("anu@test.local")
        self.client.post("/customer/cancel", data={"booking_code": "BK1001"})
        self.assertEqual(database.get_active_seats(1), [])
        self.client.post("/logout")
        self.signin("one@test.local")
        dashboard = self.client.get("/owner/dashboard")
        self.assertIn(b"<strong>0</strong>", dashboard.data)
        detail = self.client.get("/owner/bus/1")
        self.assertIn(b"CANCELLED", detail.data)

    def test_existing_single_seat_rows_migrate_to_booking_seats(self):
        legacy_dir = tempfile.TemporaryDirectory()
        legacy_path = Path(legacy_dir.name) / "legacy.db"
        with database.get_connection(legacy_path) as connection:
            connection.executescript("""
                CREATE TABLE buses (id INTEGER PRIMARY KEY, owner_name TEXT, bus_number TEXT UNIQUE, bus_name TEXT, source TEXT, destination TEXT, departure_time TEXT, arrival_time TEXT, total_seats INTEGER, created_at TEXT);
                CREATE TABLE bookings (id INTEGER PRIMARY KEY, booking_code TEXT UNIQUE, bus_id INTEGER, passenger_name TEXT, phone TEXT, seat_number INTEGER, status TEXT, created_at TEXT);
                INSERT INTO buses VALUES (1, 'Owner', 'OLD-1', 'Old Bus', 'A', 'B', '08:00', '09:00', 30, CURRENT_TIMESTAMP);
                INSERT INTO bookings VALUES (1, 'BK1001', 1, 'Old Passenger', '9876543210', 14, 'ACTIVE', CURRENT_TIMESTAMP);
            """)
        database.init_db(legacy_path)
        with database.get_connection(legacy_path) as connection:
            migrated = connection.execute("SELECT seat_number FROM booking_seats WHERE booking_id = 1").fetchone()
        self.assertEqual(migrated[0], "L14")
        legacy_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
