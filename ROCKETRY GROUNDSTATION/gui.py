import serial
import serial.tools.list_ports
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import *
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from datetime import datetime
import threading
import csv
import os

# ---------- SERIAL CONFIG ----------
BAUD = 115200
PORT = None
ser = None
running = False

# ---------- DATA STORAGE ----------
data_buffers = {
    "time": [],
    "altitude": [],
    "pressure": [],
    "temp": [],
    "ax": [],
    "ay": [],
    "az": [],
    "gx": [],
    "gy": [],
    "gz": [],
}
current_data = {
    "Team ID": "--",
    "Time": "--",
    "Alt": "--",
    "Pressure": "--",
    "Temp": "--",
    "Ax": "--",
    "Ay": "--",
    "Az": "--",
    "Gx": "--",
    "Gy": "--",
    "Gz": "--",
    "Servo": "--",
}

# ---------- GUI SETUP ----------
root = ttk.Window(themename="cyborg")
root.title("CanSat Telemetry Dashboard")
root.geometry("1500x750")  # Adjusted width to accommodate sidebar

# ---------- HEADER ----------
header_frame = ttk.Frame(root)
header_frame.pack(fill=X, pady=5)

header_label = ttk.Label(header_frame, text="Telemetry Dashboard", font=("Segoe UI", 20, "bold"))
header_label.pack()

# ---------- SIDEBAR LEFT (Download CSV) ----------
sidebar_left = ttk.Frame(root, width=200, relief="solid", borderwidth=1)
sidebar_left.pack(side=LEFT, fill=Y, padx=5)

# India Flag, Arka logo, Space Logo
india_flag = PhotoImage(file="indian_flag.jpg")  # Replace with actual image file
arka_logo = PhotoImage(file="arka_logo.png")  # Replace with actual image file
space_logo = PhotoImage(file="cbit.png")  # Replace with actual image file

ttk.Label(sidebar_left, image=india_flag).pack(pady=5)
ttk.Label(sidebar_left, image=arka_logo).pack(pady=5)
ttk.Label(sidebar_left, image=space_logo).pack(pady=5)

# Download CSV Button
def download_csv():
    # Generate CSV file from data_buffers
    filename = "telemetry_data.csv"
    try:
        with open(filename, "w", newline='') as csvfile:
            fieldnames = list(current_data.keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for i in range(len(data_buffers["time"])):
                row = {key: data_buffers[key][i] for key in fieldnames}
                writer.writerow(row)
        status_label.config(text=f"CSV saved as {filename}", bootstyle="success")
    except Exception as e:
        status_label.config(text=f"Error saving CSV: {e}", bootstyle="danger")

download_csv_btn = ttk.Button(sidebar_left, text="Download CSV", command=download_csv, bootstyle="primary-outline")
download_csv_btn.pack(pady=10)

# ---------- SIDEBAR RIGHT (CSV Data Table) ----------
sidebar_right = ttk.Frame(root, width=400, relief="solid", borderwidth=1)
sidebar_right.pack(side=RIGHT, fill=Y, padx=5)

table_frame = ttk.Frame(sidebar_right)
table_frame.pack(padx=5, pady=5)

# Add headers for the table
table_headers = list(current_data.keys())
for col, header in enumerate(table_headers):
    ttk.Label(table_frame, text=header, font=("Segoe UI", 10, "bold")).grid(row=0, column=col, padx=3, pady=3)

# ---------- SERIAL CONFIGURATION ----------
frame_top = ttk.Frame(root)
frame_top.pack(fill=X, pady=5)

ports = [port.device for port in serial.tools.list_ports.comports()]
port_var = ttk.StringVar(value=ports[0] if ports else "")
ttk.Label(frame_top, text="Serial Port:", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=5)
ttk.Combobox(frame_top, textvariable=port_var, values=ports, width=15, state="readonly").pack(side=LEFT, padx=5)

# Buttons
def start_serial():
    global ser, running, PORT
    try:
        PORT = port_var.get()
        ser = serial.Serial(PORT, BAUD, timeout=1)
        running = True
        threading.Thread(target=read_serial, daemon=True).start()
        start_btn.config(state=DISABLED)
        stop_btn.config(state=NORMAL)
        status_label.config(text=f"Connected to {PORT}", bootstyle="success")
    except Exception as e:
        status_label.config(text=f"Error: {e}", bootstyle="danger")

def stop_serial():
    global running
    running = False
    try:
        if ser and ser.is_open:
            ser.close()
    except:
        pass
    start_btn.config(state=NORMAL)
    stop_btn.config(state=DISABLED)
    status_label.config(text="Disconnected", bootstyle="warning")

start_btn = ttk.Button(frame_top, text="Start", command=start_serial, bootstyle="success-outline")
stop_btn = ttk.Button(frame_top, text="Stop", command=stop_serial, bootstyle="danger-outline", state=DISABLED)
start_btn.pack(side=LEFT, padx=5)
stop_btn.pack(side=LEFT, padx=5)

status_label = ttk.Label(frame_top, text="Disconnected", font=("Consolas", 10))
status_label.pack(side=LEFT, padx=10)

last_packet_label = ttk.Label(frame_top, text="Last packet: --", font=("Consolas", 10))
last_packet_label.pack(side=RIGHT, padx=10)

# ---------- TELEMETRY BOXES ----------
frame_mid = ttk.Frame(root)
frame_mid.pack(fill=X, pady=5)

keys = list(current_data.keys())
boxes = {}
for i, key in enumerate(keys):
    frm = ttk.Frame(frame_mid, relief="solid", borderwidth=1)
    frm.grid(row=0, column=i, padx=3, pady=3)
    ttk.Label(frm, text=key, font=("Segoe UI", 9, "bold")).pack()
    boxes[key] = ttk.Label(frm, text="--", width=8, font=("Consolas", 10))
    boxes[key].pack()

# ---------- PLOTS ----------
fig = Figure(figsize=(12, 5), dpi=100)
axs = fig.subplots(2, 3)
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(fill=BOTH, expand=True)

def style(ax, title):
    ax.set_title(title, color="white", fontsize=10)
    ax.set_facecolor("#111")
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    fig.patch.set_facecolor("#222")

# ---------- SERIAL READER ----------
def read_serial():
    global running
    while running:
        try:
            line = ser.readline().decode().strip()
            if not line:
                continue
            # Example expected format (CSV):
            # TEAM_ID,TIME,ALT,PRESSURE,TEMP,AX,AY,AZ,GX,GY,GZ,SERVO
            parts = line.split(",")
            if len(parts) < 12:
                continue

            current_data["Team ID"] = parts[0]
            current_data["Time"] = parts[1]
            current_data["Alt"] = float(parts[2])
            current_data["Pressure"] = float(parts[3])
            current_data["Temp"] = float(parts[4])
            current_data["Ax"] = float(parts[5])
            current_data["Ay"] = float(parts[6])
            current_data["Az"] = float(parts[7])
            current_data["Gx"] = float(parts[8])
            current_data["Gy"] = float(parts[9])
            current_data["Gz"] = float(parts[10])
            current_data["Servo"] = parts[11]

            data_buffers["time"].append(datetime.now().strftime("%H:%M:%S"))
            data_buffers["altitude"].append(current_data["Alt"])
            data_buffers["pressure"].append(current_data["Pressure"])
            data_buffers["temp"].append(current_data["Temp"])
            data_buffers["ax"].append(current_data["Ax"])
            data_buffers["ay"].append(current_data["Ay"])
            data_buffers["az"].append(current_data["Az"])
            data_buffers["gx"].append(current_data["Gx"])
            data_buffers["gy"].append(current_data["Gy"])
            data_buffers["gz"].append(current_data["Gz"])

            # Update CSV Table
            for i, key in enumerate(table_headers):
                ttk.Label(table_frame, text=str(current_data.get(key, "--")), font=("Consolas", 9)).grid(row=1, column=i, padx=3, pady=3)

        except Exception as e:
            status_label.config(text=f"Error reading: {e}", bootstyle="danger")

# ---------- GUI UPDATER ----------
def update_gui():
    for key, lbl in boxes.items():
        lbl.config(text=str(current_data.get(key, "--")))
        if key == "Servo":
            servo_val = str(current_data["Servo"]).lower()
            if servo_val in ["1", "deployed", "yes", "true"]:
                lbl.config(bootstyle="success")
            else:
                lbl.config(bootstyle="danger")

    axs[0,0].cla(); style(axs[0,0],"Altitude vs Time")
    axs[0,0].plot(data_buffers["time"], data_buffers["altitude"], color="lime")

    axs[0,1].cla(); style(axs[0,1],"Pressure vs Time")
    axs[0,1].plot(data_buffers["time"], data_buffers["pressure"], color="orange")

    axs[0,2].cla(); style(axs[0,2],"Temp vs Time")
    axs[0,2].plot(data_buffers["time"], data_buffers["temp"], color="red")

    axs[1,0].cla(); style(axs[1,0],"Ax,Ay,Az")
    axs[1,0].plot(data_buffers["time"], data_buffers["ax"], label="Ax")
    axs[1,0].plot(data_buffers["time"], data_buffers["ay"], label="Ay")
    axs[1,0].plot(data_buffers["time"], data_buffers["az"], label="Az")
    axs[1,0].legend(facecolor="#111", labelcolor='white', fontsize=8)

    axs[1,1].cla(); style(axs[1,1],"Gx,Gy,Gz")
    axs[1,1].plot(data_buffers["time"], data_buffers["gx"], label="Gx")
    axs[1,1].plot(data_buffers["time"], data_buffers["gy"], label="Gy")
    axs[1,1].plot(data_buffers["time"], data_buffers["gz"], label="Gz")
    axs[1,1].legend(facecolor="#111", labelcolor='white', fontsize=8)

    # ✅ Fixed Servo status display
    axs[1,2].cla(); style(axs[1,2],"Servo Status")
    servo_val = str(current_data["Servo"]).lower()
    if servo_val in ["1", "deployed", "yes", "true"]:
        s_color = "lime"
        s_text = "DEPLOYED"
    else:
        s_color = "red"
        s_text = "NOT DEPLOYED"
    axs[1,2].text(0.5, 0.5, s_text, ha="center", va="center", fontsize=16, color=s_color, transform=axs[1,2].transAxes)
    axs[1,2].axis("off")

    canvas.draw()
    last_packet_label.config(text=f"Last packet: {datetime.now().strftime('%H:%M:%S')}")
    root.after(1000, update_gui)

update_gui()
root.mainloop()
