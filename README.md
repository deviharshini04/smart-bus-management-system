# SMART BUS SEAT AND ROUTE MANAGEMENT SYSTEM

## Project goal

Smart Bus is a local undergraduate prototype with two role-based portals:

- **Bus Owner** — register buses, routes, lower/upper deck capacity, and view reservations.
- **Customer** — search routes, choose a lower- or upper-deck seat, book it, and cancel it.

It is intentionally not a production transportation platform. It does not use
GPS, maps, real bus hardware, external APIs, payments, notifications, or cloud
services.

## Technology

- Python 3 and Flask
- Java standard classes and command-line OOP logic
- SQLite at `data/smartbus.db`
- HTML and CSS only for the browser UI
- Werkzeug password hashing with Flask sessions
- Python `subprocess` calling the local Java `BridgeMain`

No JavaScript, React, Node.js, Bootstrap, Tailwind, Spring Boot, MySQL,
Firebase, Supabase, or external authentication provider is used.

## Block 9 and Block 10 additions

- Local sign up, sign in, logout, hashed passwords, and role checks.
- Owner accounts only see their own buses.
- Customer accounts search all registered buses and see their booking history.
- Safe SQLite migration for users, owner/customer relationships, deck capacity,
  and customer booking ownership.
- Double-deck bus registration with calculated total capacity.
- Bus-style lower and upper deck seat layouts using normal HTML checkboxes.
- Seat identifiers such as `L01` and `U14`.
- Owner dashboard statistics, travel cards, booking table, and seat preview.
- Customer route dashboard, result cards, booking confirmation, and cancellation.
- Multi-seat booking from 1 to 6 seats per reservation.
- `booking_seats` migration/table preserving existing single-seat bookings.
- Checkbox-based multi-seat selection with server-side exact-count validation.
- Atomic all-or-nothing booking insertion and full-reservation cancellation.
- Seat-count statistics based on active seats, not booking-record count.

## Architecture

Flask remains the only web server. Python owns authentication, sessions,
SQLite operations, form handling, page rendering, and route-level access
control. Java remains a local validation layer for seat IDs, availability,
booking validation, and cancellation validation. Python invokes Java through
`java_bridge.py`; no sockets, REST service, or Java web server is used.

## Structure

```text
AGENTS.md
README.md
.gitignore
python/
  app.py
  database.py
  java_bridge.py
  requirements.txt
  templates/
  static/style.css
java/src/
  Bus.java
  Route.java
  Booking.java
  SeatManager.java
  BookingManager.java
  BridgeMain.java
data/smartbus.db
tests/test_app.py
```

## Run locally

From the project root:

```text
cd python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Windows Command Prompt:

```text
.venv\Scripts\activate
```

Windows PowerShell:

```text
.venv\Scripts\Activate.ps1
```

Open <http://127.0.0.1:5000>. A JDK is required; the bridge compiles Java
classes automatically into the ignored `java/bin/` directory.

Manual Java check from the project root:

```text
mkdir -p java/bin
javac -d java/bin java/src/*.java
java -cp java/bin BridgeMain CHECK_SEAT 20 20 NONE U14
```

## Demonstration flow

1. Create an `OWNER` account and sign in.
2. Register a bus with 20 lower-deck and 20 upper-deck seats.
3. Sign out and create a `CUSTOMER` account.
4. Search the owner’s route and open the seat view.
5. Book `U14`; the confirmation identifies it as Upper Deck.
6. Customer history shows all three seats; the owner dashboard shows 37 available seats.
7. Cancel the booking and verify that all three seats become available again.

## Tests

```text
python/.venv/bin/python -m unittest discover -s tests -v
```

The seven isolated tests cover account creation, duplicate email, password
validation, sign in, logout, role protection, owner-only bus visibility,
1-, 2-, and 6-seat bookings, invalid quantities, exact-count validation,
mixed-deck Java validation, all-or-nothing rejection, customer history,
owner seat counts, full cancellation, and migration of legacy single-seat rows.

## Limitations and future scope

This remains a local academic prototype with intentionally simple session
authentication and no production security model. Future scope could include
mobile support, live GPS, QR tickets, online payments, notifications, and
cloud deployment, but none of those features are implemented.
