"""Local subprocess bridge from Flask to the Java command-line logic."""

from pathlib import Path
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parent.parent
JAVA_SOURCE_DIR = PROJECT_ROOT / "java" / "src"
JAVA_OUTPUT_DIR = PROJECT_ROOT / "java" / "bin"


def ensure_compiled():
    JAVA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    bridge_class = JAVA_OUTPUT_DIR / "BridgeMain.class"
    source_files = sorted(JAVA_SOURCE_DIR.glob("*.java"))
    if not source_files:
        raise RuntimeError("Java source files were not found")
    newest_source = max(source.stat().st_mtime for source in source_files)
    if not bridge_class.exists() or bridge_class.stat().st_mtime < newest_source:
        result = subprocess.run(
            ["javac", "-d", str(JAVA_OUTPUT_DIR), *map(str, source_files)],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Java compilation failed")


def run_java(command, *arguments):
    """Run BridgeMain and return its pipe-delimited response."""
    ensure_compiled()
    result = subprocess.run(
        ["java", "-cp", str(JAVA_OUTPUT_DIR), "BridgeMain", command, *map(str, arguments)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Java execution failed")
    output = result.stdout.strip()
    if "|" not in output:
        raise RuntimeError("Invalid Java response")
    status, message = output.split("|", 1)
    if status != "OK":
        raise ValueError(message)
    return message


def check_seat(lower_deck_seats, upper_deck_seats, booked_seats, requested_seat):
    booked = ",".join(map(str, booked_seats)) or "NONE"
    return run_java("CHECK_SEAT", lower_deck_seats, upper_deck_seats, booked, requested_seat)


def available_count(lower_deck_seats, upper_deck_seats, booked_seats):
    booked = ",".join(map(str, booked_seats)) or "NONE"
    return int(run_java("AVAILABLE_COUNT", lower_deck_seats, upper_deck_seats, booked))


def validate_booking(lower_deck_seats, upper_deck_seats, booked_seats, requested_seats, passenger_name, phone):
    booked = ",".join(map(str, booked_seats)) or "NONE"
    requested = ",".join(map(str, requested_seats)) or "NONE"
    return run_java("VALIDATE_BOOKING", lower_deck_seats, upper_deck_seats, booked, requested, passenger_name, phone)


def validate_cancellation(status):
    return run_java("VALIDATE_CANCEL", status)
