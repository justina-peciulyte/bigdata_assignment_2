from multiprocessing import Pool
from collections import defaultdict
from reader import chunk_reader
from worker import process_chunk
import argparse
import time
import psutil
import csv
from tqdm import tqdm
from typing import Dict, Any

# Aggregate results are written to a final CSV file after processing all chunks.
# Chunk size and number of workers can be adjusted to tune performance and later create graphics.

def parse_args():
    """Parses command-line arguments for input file, output file, and top N vessels to display."""
    parser = argparse.ArgumentParser(description="AIS Anomaly Scanner - Detects suspicious vessel behavior based on AIS data.")
    parser.add_argument("--input", type=str, required=True, help="Path to AIS CSV input file (must be mounted into the container).")
    parser.add_argument("--output", type=str, default=None, help="Path to optional CSV output file.")
    parser.add_argument("--top", type=int, default=10, help="Number of top suspicious vessels to display (default: 10).")
    parser.add_argument("--chunksize", type=int, default=50000, help="Number of rows per chunk for processing (default: 50000).")
    parser.add_argument("--workers", type=int, default=4, help="Number of worker processes to use (default: 4, sequential mode: 1).")

    args = parser.parse_args()
    return args


def fix_mb(bytes_value):
    """Helper function to convert bytes to megabytes."""
    return bytes_value / (1024 * 1024)


def print_summary(results, top_n):
    """Prints a summary of the results, including top vessels by suspiciousness score."""
    print("\n=== AIS Anomaly Summary ===")
    
    total_vessels = len(results)
    total_dark = sum(r["going_dark"] for r in results.values())
    total_jumps = sum(r["jumps"] for r in results.values())
    
    print(f"Total vessels analyzed: {total_vessels}")
    print(f"Total 'going dark' events: {total_dark}")
    print(f"Total 'impossible jumps' events: {total_jumps}")

    print(f"\nTop {top_n} suspicious vessels:")
    sorted_vessels = sorted(results.items(), key=lambda x: (x[1]["score"]), reverse=True)

    for i, (mmsi, data) in enumerate(sorted_vessels[:top_n], start=1):
        print(f"{i}. MMSI: {mmsi} | Score: {data['score']:.2f} | Going Dark: {data['going_dark']} | Impossible Jumps: {data['jumps']}")


def aggregate_results(chunk_results):
    """Merges all chunk-level vessel results into a single vessel-level dictionary."""
    merged: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "going_dark": 0,
        "jumps": 0,
        "score": 0.0,
        "max_gap_hours": 0.0,
        "max_gap_event": "No movement during blackout",
        "impossible_jumps_nm": 0.0,
        "worst_jump_event": "No impossible jump",
    })

    for chunk_result in chunk_results:
        vessels = chunk_result.get("vessels", {})
        for mmsi, vessel_data in vessels.items():
            anomalies = vessel_data.get("anomalies", {})

            gd = anomalies.get("going_dark", 0)
            jumps = anomalies.get("jumps", 0)

            merged[mmsi]["going_dark"] += gd
            merged[mmsi]["jumps"] += jumps
            merged[mmsi]["score"] = merged[mmsi]["max_gap_hours"]*0.5 + merged[mmsi]["impossible_jumps_nm"]*0.1

            chunk_gap = float(vessel_data.get("max_gap_hours", 0.0) or 0.0)
            if chunk_gap > merged[mmsi]["max_gap_hours"]:
                merged[mmsi]["max_gap_hours"] = chunk_gap
                merged[mmsi]["max_gap_event"] = vessel_data.get("max_gap_event", "No movement during blackout")

            merged[mmsi]["impossible_jumps_nm"] += float(vessel_data.get("impossible_jumps_nm", 0.0) or 0.0)

            chunk_worst_jump = vessel_data.get("worst_jump_event", "No impossible jump")
            if merged[mmsi]["worst_jump_event"] == "No impossible jump" and chunk_worst_jump != "No impossible jump":
                merged[mmsi]["worst_jump_event"] = chunk_worst_jump

    return dict(merged)


def write_results_csv(results, output_path):
    """Writes merged per-vessel anomaly results to a CSV file."""
    fieldnames = [
        "MMSI",
        "score",
        "going_dark",
        "jumps",
        "max_gap_hours",
        "impossible_jumps_nm",
        "max_gap_event",
        "worst_jump_event",
    ]

    # The output file is sorted by the suspiciousness score in descending order.
    sorted_rows = sorted(results.items(), key=lambda item: item[1]["score"], reverse=True)

    with open(output_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for mmsi, data in sorted_rows:
            writer.writerow({
                "MMSI": mmsi,
                "score": f"{data['score']:.2f}",
                "going_dark": data["going_dark"],
                "jumps": data["jumps"],
                "max_gap_hours": f"{data['max_gap_hours']:.2f}",
                "impossible_jumps_nm": f"{data['impossible_jumps_nm']:.2f}",
                "max_gap_event": data["max_gap_event"],
                "worst_jump_event": data["worst_jump_event"],
            })


def main():
    """Main function to orchestrate the AIS anomaly scanning process."""
    args = parse_args()
    start_time = time.time()
    all_results = []

    print(f"Input file: {args.input}")
    print(f"Output file: {args.output}")
    print(f"Top N vessels: {args.top}")
    print(f"Chunk size: {args.chunksize}")
    print(f"Number of workers: {args.workers}")

    print("Pipeline started successfully. Streaming chunks for processing...")
    processed_chunks = 0

    workers = max(1, args.workers)
    # If only one worker is specified, process chunks sequentially in the main thread. 
    if workers == 1:
        for task in tqdm(chunk_reader(args.input, chunksize=args.chunksize), desc="Processing chunks", unit="chunks", colour="green"):
            chunk_result = process_chunk(task)
            all_results.append(chunk_result)
            processed_chunks += 1
    # Otherwise, use multiprocessing Pool to process chunks in parallel.
    else:
        with Pool(processes=workers) as pool:
            chunk_stream = chunk_reader(args.input, chunksize=args.chunksize)
            for chunk_result in tqdm(pool.imap_unordered(process_chunk, chunk_stream), desc="Processing chunks", unit="chunks", colour="green"):
                all_results.append(chunk_result)
                processed_chunks += 1

    if processed_chunks == 0:
        print("No data found in input file.")
        return

    merged_results = aggregate_results(all_results)
    if args.output:
        write_results_csv(merged_results, args.output)
        print(f"\nResults written to: {args.output}")
    print_summary(merged_results, args.top)

    elapsed = time.time() - start_time
    process = psutil.Process()
    memory_mb = fix_mb(process.memory_info().rss)

    print(f"Runtime: {elapsed:.2f} s")
    print(f"Memory usage (RSS): {memory_mb:.2f} MB")

if __name__ == "__main__":
    main()