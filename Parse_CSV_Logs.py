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
ACTUAL_POSITION = []

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
                ACTUAL_POSITION.append(raw_data[17])
            else:
                print(f"ERROR: raw_data length is not match. {len(raw_data)}")
        index = index + 1

def calculate_movement_time_average(movement_statuses, actual_position_value, time_index_np):
    time_diff_array = []
    position = np.array(actual_position_value, dtype=int)
    statuses = np.array(movement_statuses, dtype=int)
    
    start_position_indices = np.where((statuses == 1) & (position == 80))
    end_position_indices = np.where((statuses == 1) & (position == 180))


    print(len(start_position_indices[0]))
    print(len(end_position_indices[0]))

    for i in range(len(start_position_indices[0])):
        time_diff_array.append(abs(time_index_np[end_position_indices[0][i]] - time_index_np[start_position_indices[0][i]]))
        
    return np.mean(time_diff_array)
        

try:
    time_index_np = np.array(TIME_INDEX_STR, dtype=np.int64)
    move_status_np = np.array(MOVEMENT_STATUS_STR, dtype=int)
    actual_positions_np = np.array(ACTUAL_POSITION, dtype=int)
except ValueError as e:
    print(f"\nError converting data types: {e}")
    sys.exit(1)

average_time = calculate_movement_time_average(move_status_np, actual_positions_np, time_index_np)


print(average_time)
