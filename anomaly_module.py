from haversine_dist import haversine_distance

# Mini anomaly module for checking going dark and impossible jump events.

GOING_DARK_THRESHOLD_SECONDS = 4 * 3600
SPEED_THRESHOLD_KNOTS = 60.0

def going_dark_check(track):
    """Checks for gaps of > 4 hours between pings where the geographic position of 
    disappearance and reappearance implies the ship kept moving."""
    
    # 0. If there are fewer than 2 pings, anomaly cannot be determined.
    if len(track) < 2:
        return 0, 0.0, "No movement during blackout"

    # 1. Initialize variables to track the longest gap and the count of going dark events.
    max_gap_hours = 0.0
    max_gap_event = "No movement during blackout"
    count = 0

    # 2. Iterate through consecutive pings and check for gaps between them. Skip carryover pings as they are not part of the same track.
    for previous, current in zip(track, track[1:]):
        t1, lat1, lon1, _ = previous
        t2, lat2, lon2, current_is_carryover = current

        if current_is_carryover:
            continue

        # 3. Calculate the time gap between the two pings and if it exceeds the threshold.
        gap_seconds = (t2 - t1).total_seconds()
        if gap_seconds <= GOING_DARK_THRESHOLD_SECONDS:
            continue

        # 4. Calculate the distance between the two pings. If the ship moved during the gap, add to the event count.
        distance_nm = haversine_distance(lat1, lon1, lat2, lon2)
        gap_hours = gap_seconds / 3600.0

        if distance_nm > 0:
            count += 1

            # 5. Update the longest gap event information if this gap is the longest observed.
            if gap_hours > max_gap_hours:
                max_gap_hours = gap_hours
                max_gap_event = (
                    f"[{t1}] Lat: {lat1}, Lon: {lon1} ---> [{t2}] Lat: {lat2}, Lon: {lon2} | "
                    f"(Longest blackout: {gap_hours:.2f} h; Travel distance: {distance_nm * 1.852:.1f} km)"
                )
    # 6. Result is the count of going dark events and the longest gap event details.
    return count, max_gap_hours, max_gap_event

#

def impossible_jump_check(track):
    """Checks for jumps between consecutive pings, where the required speed would be impossible."""
    
    # 0. If there are fewer than 2 pings, anomaly cannot be determined.
    if len(track) < 2:
        return 0, 0.0, "No impossible jump"
    
    # 1. Initialize variables to track the count of impossible jump events and the maximum speed observed. 
    count = 0
    total_jump_distance_nm = 0.0
    max_single_jump = 0.0
    worst_jump_event = "No impossible jump"

    # 2. Iterate through consecutive pings and check for jumps between them. Skip carryover pings as they are not part of the same track.
    for i in range(1, len(track)):
        t1, lat1, lon1, *_ = track[i-1]
        t2, lat2, lon2, carryover2 = track[i]
        # Skip if the destination point is a carryover, as it is not part of the same track.
        if carryover2:
            continue

        # 3. Calculate the time difference in hours and the distance in nautical miles between the two pings.
        time_diff_hours = (t2 - t1).total_seconds() / 3600.0
        distance_nm = haversine_distance(lat1, lon1, lat2, lon2)

        # 4. Handle edge case where time difference is zero to avoid division by zero.
        if time_diff_hours == 0:
            if distance_nm > 0:
                count += 1
                total_jump_distance_nm += distance_nm
            continue

        # 5. Calculate the speed in knots and check against the threshold for impossible jumps.
        speed_knots = distance_nm / time_diff_hours
        if speed_knots > SPEED_THRESHOLD_KNOTS and distance_nm > 1.0:
            count += 1
            total_jump_distance_nm += distance_nm
            # 6. Update the worst jump event information if this jump is the longest observed.
            if distance_nm > max_single_jump:
                max_single_jump = distance_nm
                worst_jump_event = (
                    f"[{t1}] Lat: {lat1}, Lon: {lon1} ---> [{t2}] Lat: {lat2}, Lon: {lon2} | "
                    f"(Longest jump distance: {distance_nm * 1.852:.1f} km)"
                )
    # 7. Result is the count of impossible jump events, total distance of jumps, and the worst jump event details.
    return count, total_jump_distance_nm, worst_jump_event