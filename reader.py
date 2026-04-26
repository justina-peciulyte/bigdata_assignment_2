from collections import deque
from typing import Iterator, List, Tuple

Chunk_task = Tuple[int, str, int, int, str, List[str]]

def chunk_reader(input_path: str, chunksize: int = 50000, overlap_rows: int = 2000) -> Iterator[Chunk_task]:
    """Reads the input CSV file in chunks and creates tasks for workers."""
    with open(input_path, "rb") as file:
        header_bytes = file.readline()
        if not header_bytes:
            return
        
        header = header_bytes.decode("utf-8")
        chunk_index = 0
        chunk_start = file.tell()
        rows_in_chunk = 0

        carryover_for_chunk: List[str] = [] # Saves the last rows of previous chunk for overlap.
        recent_lines = deque(maxlen=max(0, overlap_rows)) # Keeps track of the most recent rows for overlap.
        
        while True:
            line = file.readline()
            if not line:
                if rows_in_chunk > 0:
                    chunk_index += 1
                    yield chunk_index, input_path, chunk_start, file.tell(), header, carryover_for_chunk
                break
            
            rows_in_chunk += 1
            if overlap_rows > 0:
                recent_lines.append(line.decode("utf-8"))

            if rows_in_chunk >= chunksize:
                chunk_index += 1
                yield chunk_index, input_path, chunk_start, file.tell(), header, carryover_for_chunk
                carryover_for_chunk = list(recent_lines) if overlap_rows > 0 else []
                chunk_start = file.tell()
                rows_in_chunk = 0
                recent_lines.clear()