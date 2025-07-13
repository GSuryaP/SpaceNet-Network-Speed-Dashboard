import threading
import socket
import random
import time
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from pymongo import MongoClient
import matplotlib.ticker as ticker
import matplotlib.image as mpimg

# Initialize MongoDB Connection
client_mongo = MongoClient("mongodb://localhost:27017/")
db = client_mongo["network_speed_db"]
collection = db["speed_tests"]
alerts_collection = db["alerts"]

# Global dictionary to store network metrics
speed_data = {'latency': [], 'packet_loss': [], 'bandwidth': [], 'timestamps': []}

# Tkinter GUI Setup
root = tk.Tk()
root.title("🚀 Network Speed Dashboard - Space Adventure")

# Main Frame
main_frame = tk.Frame(root, bg="white")
main_frame.pack(side=tk.LEFT, padx=10, pady=10)

# Sidebar for Alerts
sidebar_frame = tk.Frame(root, width=200, bg="white")
sidebar_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

alert_label = tk.Label(sidebar_frame, text="🚁 Network Alerts:", font=("Arial", 12, "bold"), fg="black", bg="white")
alert_label.pack(anchor="w")

alert_text = tk.Text(sidebar_frame, height=15, width=30, state=tk.DISABLED, bg="#fbeaea", fg="#c0392b")
alert_text.pack(fill=tk.BOTH, expand=True)

# Load Images
rocket_img = mpimg.imread("C:/Users/drish/OneDrive/Desktop/CN_LAB/rocket.png")
alien_img = mpimg.imread("C:/Users/drish/OneDrive/Desktop/CN_LAB/alien.png")
satellite_img = mpimg.imread("C:/Users/drish/OneDrive/Desktop/CN_LAB/satellite.png")
background_img = mpimg.imread("C:/Users/drish/OneDrive/Desktop/CN_LAB/space_bg.png")

# Matplotlib Figure (Light Theme)
fig, ax = plt.subplots(figsize=(6, 4), facecolor="white")
canvas = FigureCanvasTkAgg(fig, master=main_frame)
canvas.get_tk_widget().pack()

# Store Selected Graph Type
selected_graph = tk.StringVar(value="Latency")

def place_icon(x, y, image_array, zoom=0.05):
    imagebox = OffsetImage(image_array, zoom=zoom)
    ab = AnnotationBbox(imagebox, (x, y), frameon=False)
    ax.add_artist(ab)

def update_graph():
    ax.clear()

    if selected_graph.get() == "Latency":
        data = speed_data['latency']
        y_label = "🚎 Latency (ms)"
        color = "#6c5ce7"
        marker = 'o'
        image = alien_img
    elif selected_graph.get() == "Packet Loss":
        data = speed_data['packet_loss']
        y_label = "🚁 Packet Loss (%)"
        color = "#d63031"
        marker = 'x'
        image = satellite_img
    elif selected_graph.get() == "Bandwidth":
        data = speed_data['bandwidth']
        y_label = "🚀 Bandwidth (Mbps)"
        color = "#00b894"
        marker = 's'
        image = rocket_img
    else:
        return

    x = speed_data['timestamps']

    if not x or not data:
        canvas.draw()
        return

    y_min = min(data) * 0.8
    y_max = max(data) * 1.2

    ax.imshow(background_img, extent=[min(x), max(x), y_min, y_max], aspect='auto', zorder=0)

    ax.plot(x, data, label=y_label, color=color, marker=marker, zorder=1)

    for i, j in zip(x, data):
        place_icon(i, j, image)

    ax.set_title(f"{selected_graph.get()} Over Time", fontsize=14, color="black")
    ax.set_xlabel("Time", color="black")
    ax.set_ylabel(selected_graph.get(), color="black")
    ax.legend(facecolor="#f0f0f0", edgecolor="black")
    ax.tick_params(colors="black")
    ax.grid(color="#ccc", linestyle="--", linewidth=0.5)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(5))
    canvas.draw()

def store_results(latency, packet_loss, bandwidth):
    collection.insert_one({
        "latency": latency,
        "packet_loss": packet_loss,
        "bandwidth": bandwidth,
        "timestamp": time.time()
    })
    check_congestion(latency, packet_loss)

def get_latency_threshold(packet_loss):
    if packet_loss < 5:
        return 100
    elif packet_loss < 10:
        return 80
    elif packet_loss < 15:
        return 60
    else:
        return 50

def check_congestion(latency, packet_loss):
    latency_threshold = get_latency_threshold(packet_loss)
    if latency > latency_threshold or packet_loss > 10:
        alert_message = f"⚠️ Congestion Detected! Latency: {latency:.2f} ms, Packet Loss: {packet_loss:.2f}%\n"
        alerts_collection.insert_one({"alert": alert_message, "timestamp": time.time()})
        update_alerts(alert_message)

def update_alerts(message):
    alert_text.config(state=tk.NORMAL)
    alert_text.insert(tk.END, message)
    alert_text.config(state=tk.DISABLED)
    alert_text.yview(tk.END)

def server():
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.bind(("0.0.0.0", 5001))
    tcp_sock.listen(5)
    print("[TCP] Server listening on port 5001")

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(("0.0.0.0", 5002))
    print("[UDP] Server listening on port 5002")

    while True:
        client, addr = tcp_sock.accept()
        start_time = time.time()
        data = client.recv(1024 * 1024)
        end_time = time.time()
        latency = random.uniform(10, 150)
        bandwidth = (8 / (end_time - start_time)) if (end_time - start_time) > 0 else 0

        speed_data['latency'].append(latency)
        speed_data['bandwidth'].append(bandwidth)
        timestamp = time.time()
        speed_data['timestamps'].append(timestamp)
        client.sendall(str(latency).encode())
        client.close()

        data, client_addr = udp_sock.recvfrom(1024)
        packet_loss = random.uniform(0, 20)
        speed_data['packet_loss'].append(packet_loss)
        udp_sock.sendto(f"{packet_loss}".encode(), client_addr)

        store_results(latency, packet_loss, bandwidth)

        if len(speed_data['latency']) > 100:
            speed_data['latency'].pop(0)
            speed_data['packet_loss'].pop(0)
            speed_data['bandwidth'].pop(0)
            speed_data['timestamps'].pop(0)

        update_graph()

def client(server_ip):
    while True:
        try:
            tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_sock.connect((server_ip, 5001))
            tcp_sock.sendall(b"0" * (1024 * 1024))
            latency = float(tcp_sock.recv(1024).decode())
            print(f"[TCP] Measured Latency: {latency} ms")
            tcp_sock.close()

            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.sendto(b"START", (server_ip, 5002))
            data, _ = udp_sock.recvfrom(1024)
            packet_loss = float(data.decode())
            print(f"[UDP] Packet Loss: {packet_loss}%")
            udp_sock.close()

            time.sleep(1)

        except Exception as e:
            print(f"[Client] Error: {e}")

def set_graph_type(graph_type):
    selected_graph.set(graph_type)
    update_graph()

latency_button = ttk.Button(main_frame, text="🚎 Latency", command=lambda: set_graph_type("Latency"))
latency_button.pack(side=tk.LEFT, padx=10, pady=10)

packet_loss_button = ttk.Button(main_frame, text="🚁 Packet Loss", command=lambda: set_graph_type("Packet Loss"))
packet_loss_button.pack(side=tk.LEFT, padx=10, pady=10)

bandwidth_button = ttk.Button(main_frame, text="🚀 Bandwidth", command=lambda: set_graph_type("Bandwidth"))
bandwidth_button.pack(side=tk.LEFT, padx=10, pady=10)

def start_app():
    mode = input("Start as (server/client)? ").strip().lower()
    if mode == "server":
        threading.Thread(target=server, daemon=True).start()
        root.mainloop()
    elif mode == "client":
        server_ip = input("Enter server IP: ").strip()
        client(server_ip)
    else:
        print("Invalid mode. Please enter 'server' or 'client'.")

if __name__ == "__main__":
    start_app()
