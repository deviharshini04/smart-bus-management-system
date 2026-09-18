/** Represents a bus registered in the Smart Bus prototype. */
public class Bus {
    private final int busId;
    private final String busNumber;
    private final String busName;
    private final String source;
    private final String destination;
    private final String departureTime;
    private final String arrivalTime;
    private final int totalSeats;

    public Bus(int busId, String busNumber, String busName, String source,
               String destination, String departureTime, String arrivalTime, int totalSeats) {
        if (totalSeats <= 0) {
            throw new IllegalArgumentException("Total seats must be positive");
        }
        this.busId = busId;
        this.busNumber = busNumber;
        this.busName = busName;
        this.source = source;
        this.destination = destination;
        this.departureTime = departureTime;
        this.arrivalTime = arrivalTime;
        this.totalSeats = totalSeats;
    }

    public int getBusId() { return busId; }
    public String getBusNumber() { return busNumber; }
    public String getBusName() { return busName; }
    public String getSource() { return source; }
    public String getDestination() { return destination; }
    public String getDepartureTime() { return departureTime; }
    public String getArrivalTime() { return arrivalTime; }
    public int getTotalSeats() { return totalSeats; }
}
