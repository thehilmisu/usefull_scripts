import serial
import sys
import time
import matplotlib.pyplot as plt

def plot_raw_data(raw_data):
    print("\n=== PLOTTING RAW DATA ===")
    print(f"Raw length: {len(raw_data)} characters\n")

    # Split and clean parts
    parts = [part.strip() for part in raw_data.split(',') if part.strip()]

    print(f"Total cleaned parts: {len(parts)}")
    if len(parts) == 0:
        print("Error: No valid data found after cleaning.")
        return

    # Ensure even number of values (x,y pairs)
    if len(parts) % 2 != 0:
        print(f"Warning: Odd number of values ({len(parts)}), removing last incomplete value.")
        parts = parts[:-1]

    # Convert to integers with error reporting
    data = []
    for i, part in enumerate(parts):
        try:
            data.append(int(part))
        except ValueError:
            print(f"Error: Cannot convert part {i} to int: '{part}'")
            return

    # Extract x and y
    y_values = data[::2]
    x_values = data[1::2]

    print(f"X values count: {len(x_values)}")
    print(f"Y values count: {len(y_values)}")

    # Plot
    plt.figure(figsize=(14, 7))
    plt.plot(x_values, marker='o', linestyle='-', color='green', markersize=3, linewidth=1, label='X Values')

    plt.title('SPI Data Plot', fontsize=16)
    plt.xlabel('Sample Index', fontsize=12)
    # plt.ylabel('Value', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


if len(sys.argv) < 2:
    print("Usage: python Serial_Plot.py <PORT>")
    print("Example (Windows): python test_serial.py COM3")
    print("Example (Mac):     python test_serial.py /dev/cu.usbmodem21401")
    print("Example (Linux):   python test_serial.py /dev/ttyACM0")
    print("\nAvailable ports:")
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        for port in ports:
            print(f"  {port.device} - {port.description}")
    except Exception as e:
        print(f"  Could not list ports: {e}")
    sys.exit(1)

port_name = sys.argv[1]

print(f"Opening {port_name} at 115200 baudrate...")
print("Press Ctrl+C to exit\n")



# Get log filename
logfile_name = input("Please enter Logfile name (without extension): ").strip()
if not logfile_name:
    logfile_name = "LOG"
logfile_name = logfile_name.replace(" ", "_").upper() + ".log"

with serial.Serial(port_name, 115200, timeout=1) as ser:
    with open(logfile_name, 'a') as txtfile:
        try:
            print(f"Listening on {port_name} at {115200} baud...")
            ser.flushOutput()
            ser.flushInput()
            
            while True:
                if ser.in_waiting > 0:
                    # Read available data
                    data = ser.readline()
                    try:
                        text = data.decode('utf-8', errors='ignore').rstrip()
                        if text:
                            print(text)
                            txtfile.write(text)
                    except:
                        # If decode fails, print as hex
                        print(f"HEX: {data.hex()}")
                else:
                    time.sleep(0.001)  # Small delay 
                

        except serial.SerialException as e:
            print(f"Error: {e}")
        except KeyboardInterrupt:
            ser.close()
            txtfile.close()
            print("Program terminated.")
            try:
                with open(logfile_name, 'r') as file:
                    raw = file.read()
                raw = raw.strip()  # Remove leading/trailing whitespace and newlines
                if not raw:
                    print(f"Error: '{logfile_name}' is empty.")
                    sys.exit(1)
            except FileNotFoundError:
                print(f"Error: File '{logfile_name}' not found.")
                sys.exit(1)
            except Exception as e:
                print(f"Error reading file: {e}")
                sys.exit(1)

            plot_raw_data(raw)
