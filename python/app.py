"""Flask web application for the local Smart Bus prototype."""

import re
import sqlite3
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import database
import java_bridge


app = Flask(__name__)
app.secret_key = "smart-bus-academic-prototype"
database.init_db()


def current_user():
    user_id = session.get("user_id")
    return database.get_user(user_id) if user_id else None


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None:
                flash("Please sign in to continue.", "error")
                return redirect(url_for("signin"))
            if user["role"] != role:
                flash("This page is not available for your account type.", "error")
                return redirect(url_for("owner_dashboard" if user["role"] == "OWNER" else "customer"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def validate_email(email):
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email))


def validate_bus_form(form, user):
    fields = {
        "owner_name": user["name"],
        "owner_user_id": user["id"],
        "bus_number": form.get("bus_number", "").strip(),
        "bus_name": form.get("bus_name", "").strip(),
        "source": form.get("source", "").strip(),
        "destination": form.get("destination", "").strip(),
        "departure_time": form.get("departure_time", "").strip(),
        "arrival_time": form.get("arrival_time", "").strip(),
        "lower_deck_seats": form.get("lower_deck_seats", "").strip(),
        "upper_deck_seats": form.get("upper_deck_seats", "0").strip(),
    }
    if any(not fields[key] for key in ("bus_number", "bus_name", "source", "destination", "departure_time", "arrival_time", "lower_deck_seats")):
        return fields, "Please complete all required bus, route, and schedule fields."
    if fields["source"].casefold() == fields["destination"].casefold():
        return fields, "From and To locations must be different."
    try:
        lower = int(fields["lower_deck_seats"])
        upper = int(fields["upper_deck_seats"])
    except ValueError:
        return fields, "Deck seat counts must be whole numbers."
    if lower < 1 or upper < 0 or lower + upper > 120:
        return fields, "Lower deck must have seats and total capacity must be between 1 and 120."
    fields["lower_deck_seats"] = lower
    fields["upper_deck_seats"] = upper
    fields["total_seats"] = lower + upper
    return fields, None


def seat_codes(prefix, count):
    return [f"{prefix}{number:02d}" for number in range(1, count + 1)]


def seat_deck(seat_code):
    return "Upper Deck" if str(seat_code).upper().startswith("U") else "Lower Deck"


def valid_seat_count(value):
    try:
        count = int(value)
    except (TypeError, ValueError):
        return None
    return count if 1 <= count <= 6 else None


def owner_bus_or_redirect(bus_id):
    bus = database.get_bus(bus_id)
    user = current_user()
    if bus is None or user is None or bus["owner_user_id"] != user["id"]:
        flash("Bus not found in your account.", "error")
        return None
    return bus


@app.get("/")
def home():
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role = request.form.get("role", "").upper()
        error = None
        if not all((name, email, password, confirm_password, role)):
            error = "All fields are required."
        elif not validate_email(email):
            error = "Enter a valid-looking email address."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif role not in {"OWNER", "CUSTOMER"}:
            error = "Choose either Bus Owner or Customer."
        elif database.get_user_by_email(email):
            error = "An account with that email already exists."
        if error:
            return render_template("signup.html", error=error, form=request.form)
        try:
            database.insert_user({
                "name": name, "email": email,
                "password_hash": generate_password_hash(password), "role": role,
            })
        except sqlite3.IntegrityError:
            return render_template("signup.html", error="An account with that email already exists.", form=request.form)
        flash("Account created. Please sign in.", "success")
        return redirect(url_for("signin"))
    return render_template("signup.html", form={})


@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        user = database.get_user_by_email(email)
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("owner_dashboard" if user["role"] == "OWNER" else "customer"))
        return render_template("signin.html", error="Email or password is incorrect.", form=request.form)
    return render_template("signin.html")


@app.post("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("home"))


@app.get("/owner")
@role_required("OWNER")
def owner():
    return redirect(url_for("owner_dashboard"))


@app.route("/owner/register", methods=["GET", "POST"])
@role_required("OWNER")
def owner_register():
    user = current_user()
    if request.method == "POST":
        fields, error = validate_bus_form(request.form, user)
        if error:
            return render_template("owner_register.html", form=fields, error=error)
        try:
            database.insert_bus(fields)
        except sqlite3.IntegrityError:
            return render_template("owner_register.html", form=fields, error="Bus number already exists.")
        flash("Bus registered successfully.", "success")
        return redirect(url_for("owner_dashboard"))
    return render_template("owner_register.html", form={})


@app.get("/owner/dashboard")
@role_required("OWNER")
def owner_dashboard():
    buses = []
    totals = {"buses": 0, "seats": 0, "booked": 0}
    for bus in database.get_all_buses(current_user()["id"]):
        booked = database.count_active_bookings(bus["id"])
        item = {"bus": bus, "booked": booked, "available": bus["total_seats"] - booked}
        buses.append(item)
        totals["buses"] += 1
        totals["seats"] += bus["total_seats"]
        totals["booked"] += booked
    totals["available"] = totals["seats"] - totals["booked"]
    return render_template("owner_dashboard.html", buses=buses, totals=totals)


@app.get("/owner/bus/<int:bus_id>")
@role_required("OWNER")
def owner_bus_detail(bus_id):
    bus = owner_bus_or_redirect(bus_id)
    if bus is None:
        return redirect(url_for("owner_dashboard"))
    active = database.get_active_seats(bus_id)
    bookings = database.get_bookings_for_bus(bus_id)
    return render_template(
        "owner_bus_detail.html", bus=bus, bookings=bookings,
        booked=len(active), available=bus["total_seats"] - len(active),
        lower_seats=seat_codes("L", bus["lower_deck_seats"]),
        upper_seats=seat_codes("U", bus["upper_deck_seats"]), active_seats=active,
    )


@app.route("/customer", methods=["GET", "POST"])
@role_required("CUSTOMER")
def customer():
    if request.method == "POST":
        return redirect(url_for("customer_search", source=request.form.get("source", ""), destination=request.form.get("destination", "")))
    return render_template("customer.html", bookings=database.get_customer_bookings(current_user()["id"]))


@app.route("/customer/search", methods=["GET", "POST"])
@role_required("CUSTOMER")
def customer_search():
    source = request.values.get("source", "").strip()
    destination = request.values.get("destination", "").strip()
    buses, error = [], None
    if not source or not destination:
        error = "Please enter both From and To locations."
    else:
        for bus in database.search_buses(source, destination):
            active = database.get_active_seats(bus["id"])
            try:
                available = java_bridge.available_count(bus["lower_deck_seats"], bus["upper_deck_seats"], active)
            except (RuntimeError, ValueError):
                available = bus["total_seats"] - len(active)
            buses.append({
                "bus": bus, "available": available,
                "lower_available": bus["lower_deck_seats"] - database.count_active_deck_seats(bus["id"], "L"),
                "upper_available": bus["upper_deck_seats"] - database.count_active_deck_seats(bus["id"], "U"),
            })
    return render_template("bus_results.html", source=source, destination=destination, buses=buses, error=error)


@app.get("/customer/bus/<int:bus_id>/seats")
@role_required("CUSTOMER")
def seat_selection(bus_id):
    bus = database.get_bus(bus_id)
    if bus is None:
        flash("Bus not found.", "error")
        return redirect(url_for("customer"))
    requested_count = valid_seat_count(request.args.get("seat_count"))
    if requested_count is None:
        return render_template("seat_quantity.html", bus=bus, error=None)
    return render_template(
        "seat_selection.html", bus=bus, requested_count=requested_count, selected_seats=[], error=None,
        booked_seats=database.get_active_seats(bus_id), lower_seats=seat_codes("L", bus["lower_deck_seats"]),
        upper_seats=seat_codes("U", bus["upper_deck_seats"]),
    )


@app.post("/customer/bus/<int:bus_id>/choose-seats")
@role_required("CUSTOMER")
def choose_seat_count(bus_id):
    bus = database.get_bus(bus_id)
    if bus is None:
        flash("Bus not found.", "error")
        return redirect(url_for("customer"))
    requested_count = valid_seat_count(request.form.get("seat_count"))
    if requested_count is None:
        return render_template("seat_quantity.html", bus=bus, error="Please choose between 1 and 6 seats.")
    return redirect(url_for("seat_selection", bus_id=bus_id, seat_count=requested_count))


@app.post("/customer/bus/<int:bus_id>/book")
@role_required("CUSTOMER")
def create_booking(bus_id):
    bus = database.get_bus(bus_id)
    if bus is None:
        flash("Bus not found.", "error")
        return redirect(url_for("customer"))
    passenger_name = request.form.get("passenger_name", "").strip()
    phone = request.form.get("phone", "").strip()
    requested_count = valid_seat_count(request.form.get("seat_count"))
    selected_seats = list(dict.fromkeys(
        seat.strip().upper() for seat in request.form.getlist("seat_number") if seat.strip()
    ))
    error = None
    if requested_count is None:
        error = "Please choose between 1 and 6 seats."
    elif len(selected_seats) != requested_count:
        error = f"Please select exactly {requested_count} seats."
    elif not passenger_name or not phone:
        error = "Passenger name and phone number are required."
    elif not phone.isdigit() or len(phone) != 10:
        error = "Phone number must contain exactly 10 digits."
    if error:
        return render_template(
            "seat_selection.html", bus=bus, requested_count=requested_count or 1,
            selected_seats=selected_seats, error=error, booked_seats=database.get_active_seats(bus_id),
            lower_seats=seat_codes("L", bus["lower_deck_seats"]), upper_seats=seat_codes("U", bus["upper_deck_seats"]),
        )
    active_seats = database.get_active_seats(bus_id)
    try:
        java_bridge.validate_booking(
            bus["lower_deck_seats"], bus["upper_deck_seats"], active_seats,
            selected_seats, passenger_name, phone,
        )
        booking_code = f"BK{database.next_booking_number()}"
        database.insert_booking({
            "booking_code": booking_code, "bus_id": bus_id,
            "passenger_name": passenger_name, "phone": phone,
            "seat_numbers": selected_seats, "customer_user_id": current_user()["id"],
        })
    except ValueError as exception:
        message = str(exception)
        if message.startswith("SEAT_UNAVAILABLE|"):
            error = f"Seat {message.split('|', 1)[1]} is no longer available. Please select your seats again."
        elif message.startswith("INVALID_SEAT|"):
            error = f"Seat {message.split('|', 1)[1]} is invalid. Please select your seats again."
        else:
            error = "Please choose valid available seats."
        return render_template(
            "seat_selection.html", bus=bus, requested_count=requested_count, selected_seats=selected_seats,
            error=error, booked_seats=database.get_active_seats(bus_id),
            lower_seats=seat_codes("L", bus["lower_deck_seats"]), upper_seats=seat_codes("U", bus["upper_deck_seats"]),
        )
    except sqlite3.IntegrityError:
        error = "One of those seats was just booked. Please select your seats again."
        return render_template(
            "seat_selection.html", bus=bus, requested_count=requested_count, selected_seats=selected_seats,
            error=error, booked_seats=database.get_active_seats(bus_id),
            lower_seats=seat_codes("L", bus["lower_deck_seats"]), upper_seats=seat_codes("U", bus["upper_deck_seats"]),
        )
    except RuntimeError:
        return render_template(
            "seat_selection.html", bus=bus, requested_count=requested_count, selected_seats=selected_seats,
            error="Java booking validation is unavailable.", booked_seats=database.get_active_seats(bus_id),
            lower_seats=seat_codes("L", bus["lower_deck_seats"]), upper_seats=seat_codes("U", bus["upper_deck_seats"]),
        )
    return redirect(url_for("booking_confirmation", booking_code=booking_code))


@app.get("/customer/booking/<booking_code>")
@role_required("CUSTOMER")
def booking_confirmation(booking_code):
    booking = database.get_booking(booking_code)
    if booking is None or (booking["customer_user_id"] not in (None, current_user()["id"])):
        flash("Booking not found in your account.", "error")
        return redirect(url_for("customer"))
    bus = database.get_bus(booking["bus_id"])
    seat_numbers = [seat.strip() for seat in (booking["seat_numbers"] or "").split(",") if seat.strip()]
    return render_template("booking_confirmation.html", booking=booking, bus=bus, seat_numbers=seat_numbers)


@app.route("/customer/cancel", methods=["GET", "POST"])
@role_required("CUSTOMER")
def cancel_booking():
    message, error = None, None
    booking_code = request.form.get("booking_code", "").strip() if request.method == "POST" else ""
    if request.method == "POST":
        booking = database.get_booking(booking_code) if booking_code else None
        if not booking:
            error = "Booking not found in your account."
        elif booking["customer_user_id"] not in (None, current_user()["id"]):
            error = "Booking not found in your account."
        else:
            try:
                java_bridge.validate_cancellation(booking["status"])
                database.cancel_booking(booking["booking_code"])
                message = f"Booking {booking['booking_code']} cancelled successfully."
            except ValueError as exception:
                error = "Booking already cancelled." if str(exception) == "ALREADY_CANCELLED" else "Booking cannot be cancelled."
            except RuntimeError:
                error = "Java cancellation validation is unavailable."
    return render_template("cancel_booking.html", booking_code=booking_code, message=message, error=error)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
