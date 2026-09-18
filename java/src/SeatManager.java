import java.util.Collection;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Validates lower- and upper-deck seat identifiers such as L01 and U14. */
public class SeatManager {
    private static final Pattern SEAT_PATTERN = Pattern.compile("^([LU])(\\d{2})$");
    private final int lowerDeckSeats;
    private final int upperDeckSeats;

    public SeatManager(int lowerDeckSeats, int upperDeckSeats) {
        if (lowerDeckSeats < 0 || upperDeckSeats < 0 || lowerDeckSeats + upperDeckSeats < 1) {
            throw new IllegalArgumentException("INVALID_CAPACITY");
        }
        this.lowerDeckSeats = lowerDeckSeats;
        this.upperDeckSeats = upperDeckSeats;
    }

    public boolean isValidSeat(String seatCode) {
        if (seatCode == null) {
            return false;
        }
        Matcher matcher = SEAT_PATTERN.matcher(seatCode.toUpperCase(Locale.ROOT));
        if (!matcher.matches()) {
            return false;
        }
        int number = Integer.parseInt(matcher.group(2));
        return "L".equals(matcher.group(1)) ? number <= lowerDeckSeats : number <= upperDeckSeats;
    }

    public boolean isSeatAvailable(Collection<String> bookedSeatCodes, String requestedSeat) {
        return isValidSeat(requestedSeat) && !bookedSeatCodes.contains(requestedSeat.toUpperCase(Locale.ROOT));
    }

    public int calculateAvailableSeats(Collection<String> bookedSeatCodes) {
        int booked = 0;
        for (String seat : bookedSeatCodes) {
            if (isValidSeat(seat)) {
                booked++;
            }
        }
        return lowerDeckSeats + upperDeckSeats - booked;
    }
}
