import pandas as pd
import numpy as np
import csv
import sys
import matplotlib.pyplot as plt

if len(sys.argv) < 2:
    print("\nUsage: python Parse_CSV_Logs.py <logfilepath>\n")
    sys.exit(1)

LOGFILE_PATH = sys.argv[1]
HEADERS = []
OVERTRAVEL = []
BLOCKAGE = []
TIME_INDEX_STR = [] 
INTERNAL_ERROR = []
CYCLE_COUNT = []
MOVEMENT_STATUS_STR = []

with open(LOGFILE_PATH, 'r') as log_file:
    reader = csv.reader(log_file)
    index = 0
    for row in reader:
        if index == 0:
            HEADERS = [part.strip() for part in row[0].split(';') if part.strip()] 
        else:
            raw_data = [part.strip() for part in row[0].split(';') if part.strip()] 
            if len(raw_data) > 8:
                TIME_INDEX_STR.append(raw_data[0]) 
                BLOCKAGE.append(raw_data[1])
                OVERTRAVEL.append(raw_data[2])
                INTERNAL_ERROR.append(raw_data[3])
                CYCLE_COUNT.append(raw_data[7])
                MOVEMENT_STATUS_STR.append(raw_data[8])
            else:
                print(f"ERROR: raw_data length is not match. {len(raw_data)}")
        index = index + 1

""" Handle potential length mismatch """
if len(TIME_INDEX_STR) > len(MOVEMENT_STATUS_STR):
    MOVEMENT_STATUS_STR.append('0')

def calculate_average_movement_time_edges(time_index_ms, movement_statuses):
   
    statuses = np.array(movement_statuses, dtype=int)
    times = np.array(time_index_ms, dtype=np.int64)

    # 1. Detect changes in status
    # np.diff([0, 0, 1, 1, 0, 1, 0]) -> [0, 1, 0, -1, 1, -1]
    # We prepend a 0 to catch the start of a movement if it begins at index 0
    status_changes = np.diff(statuses, prepend=0)

    # 2. Find indices where status changes to 1 (rising edge)
    start_indices = np.where(status_changes == 1)[0]
    
    # 3. Find indices where status changes back to 0 (falling edge)
    # end_indices = np.where(status_changes == -1)[0]
    end_indices = np.where(status_changes == 0)[0]
    
    # Handle the case where the log file ends while the device is still moving (status is 1)
    if len(end_indices) < len(start_indices):
        # Append the last timestamp as the end time of the final movement
        end_indices = np.append(end_indices, len(statuses) - 1)

    start_times = times[start_indices]
    end_times = times[end_indices]
    
    durations = [] 
    for i in range(len(end_times)):
        duration_seconds = (end_times[i] - start_times[i]) / 1000.0
        if duration_seconds >= 0:
            durations.append(duration_seconds)

    return np.mean(durations)



try:
    time_index_np = np.array(TIME_INDEX_STR, dtype=np.int64)
    move_status_np = np.array(MOVEMENT_STATUS_STR, dtype=int)
except ValueError as e:
    print(f"\nError converting data types: {e}")
    sys.exit(1)

average_time = calculate_average_movement_time_edges(time_index_np, move_status_np)

print(f"\nSuccessfully processed {len(time_index_np)} records.")
print(f"The average movement time is: {average_time:.4f} seconds")
print(f"The average movement time is: {average_time / 60.0:.4f} minutes")


