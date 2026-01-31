import asyncio
import websockets
import json
import time

# --- CONSTANTS ---
COLLEGE_LOCATION = {"lat": 12.9410, "lon": 77.5655, "name": "BMS College of Engineering"}

# Simple linear interpolation between two points
def interpolate(start, end, fraction):
    return start + (end - start) * fraction

class SimulatedBus:
    def __init__(self, bus_id, route_name, waypoints, speed_kmh=40):
        self.bus_id = bus_id
        self.route_name = route_name
        self.waypoints = waypoints # List of [lat, lon] tuples
        self.current_segment = 0
        self.progress = 0.0 # 0.0 to 1.0 of current segment
        self.speed = speed_kmh / 3600 # degrees per second approx (very rough, treating lat/lon as flat plane for simplicity)
        
        # Adjust speed factor to be realistic for lat/lon updates (1 deg ~ 111km)
        # speed_kmh / 111 = deg/hour -> / 3600 = deg/sec
        self.step_size = (speed_kmh / 111.0) / 3600 

    def move(self, dt):
        # Calculate distance of current segment to normalize speed
        start = self.waypoints[self.current_segment]
        end = self.waypoints[self.current_segment + 1]
        
        dist = ((end[0] - start[0])**2 + (end[1] - start[1])**2)**0.5
        
        if dist == 0:
            self.progress = 1.0
        else:
            # How much progress to add?
            # step_size is degrees to move per second
            # fraction = step_size / dist
            fraction = (self.step_size * dt) / dist
            self.progress += fraction

        # Check if segment complete
        if self.progress >= 1.0:
            self.progress = 0.0
            self.current_segment += 1
            # Check if route complete
            if self.current_segment >= len(self.waypoints) - 1:
                # Loop back or reverse (here we simply reset to start for continuous loop)
                self.current_segment = 0

        # Get current position
        start = self.waypoints[self.current_segment]
        end = self.waypoints[self.current_segment + 1]
        
        lat = interpolate(start[0], end[0], self.progress)
        lon = interpolate(start[1], end[1], self.progress)
        
        return lat, lon

async def simulate_bus():
    uri = "ws://localhost:8000/ws/locations"
    
    # Define approximate road waypoints (lat, lon)
    
    # Route 1: Malleshwaram -> Majestic -> Chamrajpet -> College
    # This roughly follows 8th Main -> Dhanvantri Rd -> Bull Temple Rd
    route1_waypoints = [
        [13.0055, 77.5692], # Malleshwaram
        [12.9904, 77.5705], # Seshadripuram
        [12.9796, 77.5760], # Anand Rao Circle
        [12.9652, 77.5767], # Majestic / Cottonpet
        [12.9556, 77.5647], # Chamrajpet
        [12.9410, 77.5655]  # BMS College (End)
    ]

    # Route 2: Indiranagar -> MG Road -> Corporation -> Lalbagh -> College
    route2_waypoints = [
        [12.9784, 77.6408], # Indiranagar
        [12.9740, 77.6136], # MG Road
        [12.9678, 77.5891], # Corporation Circle
        [12.9485, 77.5832], # Lalbagh West Gate
        [12.9410, 77.5655]  # BMS College (End)
    ]

    buses = [
        SimulatedBus("KA-01-FA-1234", "Rt 101: Malleshwaram -> College", route1_waypoints, speed_kmh=60),
        SimulatedBus("KA-05-SI-5678", "Rt 202: Indiranagar -> College", route2_waypoints, speed_kmh=60)
    ]
    
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Simulating buses moving along roads to College...")
            
            last_time = time.time()
            
            while True:
                now = time.time()
                dt = now - last_time # Delta time in seconds
                
                # Cap dt to avoid huge jumps if logic pauses
                if dt > 0.5: dt = 0.5 
                
                for bus in buses:
                    lat, lon = bus.move(dt * 10) # Speed up simulation 10x for visual effect
                    
                    data = {
                        "bus_id": bus.bus_id,
                        "lat": lat,
                        "lon": lon,
                        "route": bus.route_name
                    }
                    await websocket.send(json.dumps(data))
                    # print(f"Sent {bus.bus_id}: {lat:.4f}, {lon:.4f}")
                
                last_time = now
                await asyncio.sleep(1) # Send updates every second

    except ConnectionRefusedError:
        print("Failed to connect. Is the server running on localhost:8000?")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(simulate_bus())
    except KeyboardInterrupt:
        print("\nSimulation stopped.")
