/** Represents the source, destination, and schedule for a bus route. */
public class Route {
    private final String source;
    private final String destination;
    private final String departureTime;
    private final String arrivalTime;

    public Route(String source, String destination, String departureTime, String arrivalTime) {
        if (source == null || source.isBlank() || destination == null || destination.isBlank()) {
            throw new IllegalArgumentException("Route locations are required");
        }
        this.source = source;
        this.destination = destination;
        this.departureTime = departureTime;
        this.arrivalTime = arrivalTime;
    }

    public String getSource() { return source; }
    public String getDestination() { return destination; }
    public String getDepartureTime() { return departureTime; }
    public String getArrivalTime() { return arrivalTime; }
}
