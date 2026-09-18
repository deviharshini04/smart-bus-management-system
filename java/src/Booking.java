/** Represents a customer booking used by the Java validation layer. */
public class Booking {
    private final String bookingCode;
    private final int busId;
    private final String passengerName;
    private final String phone;
    private final int seatNumber;
    private String status;

    public Booking(String bookingCode, int busId, String passengerName, String phone,
                   int seatNumber, String status) {
        this.bookingCode = bookingCode;
        this.busId = busId;
        this.passengerName = passengerName;
        this.phone = phone;
        this.seatNumber = seatNumber;
        this.status = status;
    }

    public String getBookingCode() { return bookingCode; }
    public int getBusId() { return busId; }
    public String getPassengerName() { return passengerName; }
    public String getPhone() { return phone; }
    public int getSeatNumber() { return seatNumber; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}
