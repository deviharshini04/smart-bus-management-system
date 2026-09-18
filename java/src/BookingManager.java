import java.util.Collection;

/** Validates booking and cancellation requests for the Flask layer. */
public class BookingManager {
    public void validateBooking(int lowerDeckSeats, int upperDeckSeats,
                                Collection<String> bookedSeats, Collection<String> requestedSeats,
                                String passengerName, String phone) {
        SeatManager seatManager = new SeatManager(lowerDeckSeats, upperDeckSeats);
        if (passengerName == null || passengerName.isBlank() || phone == null || phone.isBlank()) {
            throw new IllegalArgumentException("MISSING_CUSTOMER_DETAILS");
        }
        for (String requestedSeat : requestedSeats) {
            if (!seatManager.isValidSeat(requestedSeat)) {
                throw new IllegalArgumentException("INVALID_SEAT|" + requestedSeat);
            }
            if (!seatManager.isSeatAvailable(bookedSeats, requestedSeat)) {
                throw new IllegalArgumentException("SEAT_UNAVAILABLE|" + requestedSeat);
            }
        }
    }

    public void validateCancellation(String status) {
        if (status == null || status.isBlank()) {
            throw new IllegalArgumentException("BOOKING_NOT_FOUND");
        }
        if ("CANCELLED".equalsIgnoreCase(status)) {
            throw new IllegalArgumentException("ALREADY_CANCELLED");
        }
        if (!"ACTIVE".equalsIgnoreCase(status)) {
            throw new IllegalArgumentException("INVALID_BOOKING_STATUS");
        }
    }
}
