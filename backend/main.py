from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import List
import asyncio
import json
import random
import database
import os

# Initialize DB on startup
database.init_db()

app = FastAPI()

# SECURITY CONFIG
# SECURITY CONFIG
# Attempt to get secret from environment, otherwise use a default (unsafe for production!)
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Static Files
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# --- AUTH HELPER FUNCTIONS ---
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = database.get_user(username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_admin(current_user = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=400, detail="Not authorized")
    return current_user

# --- MODELS ---
class UserCreate(BaseModel):
    username: str
    password: str

class BusCreate(BaseModel):
    bus_id: str
    driver_name: str
    route_stops: str

# --- AUTH ENDPOINTS ---

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = database.get_user(form_data.username)
    if not user or not database.verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"]}

@app.get("/users/me")
async def read_users_me(current_user = Depends(get_current_user)):
    return {
        "username": current_user["username"], 
        "role": current_user["role"]
    }

# --- ADMIN ENDPOINTS ---

@app.post("/register", status_code=201)
async def register_driver(user: UserCreate, current_user = Depends(get_current_active_admin)):
    success = database.create_user(user.username, user.password, "driver")
    if not success:
        raise HTTPException(status_code=400, detail="Username already registered")
    return {"message": "Driver created successfully"}

@app.post("/buses", status_code=201)
async def create_bus(bus: BusCreate, current_user = Depends(get_current_active_admin)):
    success = database.create_bus(bus.bus_id, bus.driver_name, bus.route_stops)
    if not success:
        raise HTTPException(status_code=400, detail="Bus ID already exists")
    return {"message": "Bus created successfully"}

@app.delete("/buses/{bus_id}")
async def delete_bus(bus_id: str, current_user = Depends(get_current_active_admin)):
    success = database.delete_bus(bus_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete bus")
    return {"message": "Bus deleted successfully"}

@app.get("/drivers")
async def get_drivers(current_user = Depends(get_current_active_admin)):
    return database.get_users_by_role("driver")

@app.get("/buses")
async def get_buses():
    return database.get_all_buses()

# --- LIVE TRACKING WEBSOCKETS ---

class ConnectionManager:
    def __init__(self):
        # We can store connections nicely
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass 

manager = ConnectionManager()

@app.websocket("/ws/locations")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive location update from a driver
            data = await websocket.receive_text()
            # Broadcast to everyone else (students, admins)
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)
        print(f"WS Error: {e}")

# --- SIMULATION LOGIC ---

def interpolate(start, end, fraction):
    return start + (end - start) * fraction

class SimulatedBus:
    def __init__(self, bus_id, route_name, waypoints, speed_kmh=40):
        self.bus_id = bus_id
        self.route_name = route_name
        self.waypoints = waypoints 
        self.current_segment = 0
        self.progress = 0.0 
        self.speed = speed_kmh / 3600 
        self.step_size = (speed_kmh / 111.0) / 3600 

    def move(self, dt):
        start = self.waypoints[self.current_segment]
        end = self.waypoints[self.current_segment + 1]
        dist = ((end[0] - start[0])**2 + (end[1] - start[1])**2)**0.5
        
        if dist == 0:
            self.progress = 1.0
        else:
            fraction = (self.step_size * dt) / dist
            self.progress += fraction

        if self.progress >= 1.0:
            self.progress = 0.0
            self.current_segment += 1
            if self.current_segment >= len(self.waypoints) - 1:
                self.current_segment = 0

        start = self.waypoints[self.current_segment]
        end = self.waypoints[self.current_segment + 1]
        
        lat = interpolate(start[0], end[0], self.progress)
        lon = interpolate(start[1], end[1], self.progress)
        return lat, lon

async def run_simulation():
    # Route 1: Malleshwaram -> College
    route1 = [
        [13.0055, 77.5692], [12.9904, 77.5705], [12.9796, 77.5760], 
        [12.9652, 77.5767], [12.9556, 77.5647], [12.9410, 77.5655]
    ]
    # Route 2: Indiranagar -> College
    route2 = [
        [12.9784, 77.6408], [12.9740, 77.6136], [12.9678, 77.5891], 
        [12.9485, 77.5832], [12.9410, 77.5655]
    ]

    buses = [
        SimulatedBus("KA-01-FA-1234", "Rt 101: Malleshwaram -> College", route1, speed_kmh=100),
        SimulatedBus("KA-05-SI-5678", "Rt 202: Indiranagar -> College", route2, speed_kmh=100)
    ]
    
    print("Starting background bus simulation...")
    while True:
        for bus in buses:
            lat, lon = bus.move(1) # simulate 1 second step
            data = {
                "bus_id": bus.bus_id,
                "lat": lat,
                "lon": lon,
                "route": bus.route_name
            }
            await manager.broadcast(json.dumps(data))
        
        await asyncio.sleep(1) # Update every second

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_simulation())

@app.get("/")
async def read_index():
    return FileResponse("../frontend/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
