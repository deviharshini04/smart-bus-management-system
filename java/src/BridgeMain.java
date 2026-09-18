import java.util.ArrayList;
import java.util.List;

/** The only local command-line interface between Python and Java. */
public class BridgeMain {
    public static void main(String[] args) {
        try {
            if (args.length == 0) {
                throw new IllegalArgumentException("INVALID_COMMAND");
            }
            switch (args[0].toUpperCase()) {
                case "CHECK_SEAT" -> checkSeat(args);
                case "AVAILABLE_COUNT" -> availableCount(args);
                case "VALIDATE_BOOKING" -> validateBooking(args);
                case "VALIDATE_CANCEL" -> validateCancel(args);
                default -> throw new IllegalArgumentException("INVALID_COMMAND");
            }
        } catch (NumberFormatException exception) {
            System.out.println("ERROR|INVALID_NUMBER");
        } catch (IllegalArgumentException exception) {
            System.out.println("ERROR|" + exception.getMessage());
        }
    }

    private static void checkSeat(String[] args) {
        requireArguments(args, 5);
        SeatManager manager = new SeatManager(Integer.parseInt(args[1]), Integer.parseInt(args[2]));
        List<String> booked = parseSeats(args[3]);
        String requested = args[4].toUpperCase();
        if (!manager.isValidSeat(requested)) {
            throw new IllegalArgumentException("INVALID_SEAT");
        }
        if (!manager.isSeatAvailable(booked, requested)) {
            throw new IllegalArgumentException("ALREADY_BOOKED");
        }
        System.out.println("OK|AVAILABLE");
    }

    private static void availableCount(String[] args) {
        requireArguments(args, 4);
        SeatManager manager = new SeatManager(Integer.parseInt(args[1]), Integer.parseInt(args[2]));
        System.out.println("OK|" + manager.calculateAvailableSeats(parseSeats(args[3])));
    }

    private static void validateBooking(String[] args) {
        requireArguments(args, 7);
        new BookingManager().validateBooking(
                Integer.parseInt(args[1]), Integer.parseInt(args[2]), parseSeats(args[3]),
                parseSeats(args[4]), args[5], args[6]
        );
        System.out.println("OK|VALID");
    }

    private static void validateCancel(String[] args) {
        requireArguments(args, 2);
        new BookingManager().validateCancellation(args[1]);
        System.out.println("OK|VALID");
    }

    private static List<String> parseSeats(String value) {
        List<String> seats = new ArrayList<>();
        if (value == null || value.isBlank() || "NONE".equalsIgnoreCase(value)) {
            return seats;
        }
        for (String part : value.split(",")) {
            seats.add(part.toUpperCase());
        }
        return seats;
    }

    private static void requireArguments(String[] args, int expected) {
        if (args.length != expected) {
            throw new IllegalArgumentException("INVALID_COMMAND");
        }
    }
}
