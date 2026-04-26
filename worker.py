from collections import defaultdict
from datetime import datetime
import csv
import anomaly_module

INVALID_MMSI_VALUES = {"000000000", "111111111", "222222222", "333333333", "444444444",
                       "555555555", "666666666", "777777777", "888888888", "999999999",
                       "123456789", "987654321"}

def valid_mmsi(mmsi: str) -> bool:
    """Checks if the MMSI is of the correct format and not in the list of placeholder values."""
    normalized = mmsi.strip()
    if not mmsi:
        return False
    if len(normalized) != 9 or not normalized.isdigit():
        return False
    if normalized in INVALID_MMSI_VALUES:
        return False
    return True

def valid_mobile_type(mobile_type: str) -> bool:
    """Checks if the mobile type is exactly Class A - commercial vessel."""
    value = mobile_type or ""
    return value == "Class A"

def iter_range_lines(file_obj, end_pos, header, carryover_rows):
    """Yields header, carryover rows, and rows from the input file."""
    yield header
    for row in carryover_rows:
        yield row
    while file_obj.tell() < end_pos:
        line = file_obj.readline()
        if not line:
            break
        yield line.decode("utf-8")

def process_chunk(task):
    """Processes a chunk of data, checks validity, performs anomaly checks, and returns the results."""
    chunk_index, input_path, start_pos, end_pos, header, carryover_rows = task
    vessels = defaultdict(list)
    parse_timestamp = datetime.strptime
    carryover_len = len(carryover_rows)

    # 1. Read chunk of data.
    with open(input_path, "rb") as file:
        file.seek(start_pos)
        line_iter = iter_range_lines(file, end_pos, header, carryover_rows)
        reader = csv.DictReader(line_iter)
        row_index = 0

        # If the header starts with a hashtag, remove it for proper parsing.
        if reader.fieldnames and reader.fieldnames[0].startswith("#"): 
            fieldnames = list(reader.fieldnames)
            fieldnames[0] = fieldnames[0].lstrip("#").strip()
            reader.fieldnames = fieldnames
        
        # 2. Validate and extract needed values from each row, if any column fails to parse, skip the row.
        for row in reader:
            is_carryover = row_index < carryover_len
            row_index += 1

            if not valid_mobile_type(row.get("Type of mobile")):
                continue

            mmsi = row["MMSI"]
            if not valid_mmsi(mmsi): 
                continue

            mmsi = mmsi.strip()

            try: 
                timestamp = parse_timestamp(row["Timestamp"], "%d/%m/%Y %H:%M:%S")
                lat = float(row["Latitude"])
                lon = float(row["Longitude"])
            except ValueError:
                continue

            vessels[mmsi].append((timestamp, lat, lon, is_carryover))

    results = {}

    # 3. Sort each vessel's track by timestamp.
    for mmsi, track in vessels.items():
        track.sort(key=lambda x: x[0]) 

    # 4. Perform anomaly checks for each vessel's track and store results.
    for mmsi, track in vessels.items():
        going_dark_count, max_gap_hours, max_gap_event = anomaly_module.going_dark_check(track)
        impossible_jumps_count, impossible_jump_nm, worst_jump_event = anomaly_module.impossible_jump_check(track) 

        anomalies = {"going_dark": going_dark_count,
                 "jumps": impossible_jumps_count,
        }

        results[mmsi] = {"anomalies": anomalies,
                         "max_gap_hours": max_gap_hours,
                         "max_gap_event": max_gap_event, 
                         "impossible_jumps_nm": impossible_jump_nm, 
                         "worst_jump_event": worst_jump_event
                        }

    # 5. Result for chunk is a dictionary with chunk index and the vessels' results.
    return {"chunk": chunk_index, "vessels": results}