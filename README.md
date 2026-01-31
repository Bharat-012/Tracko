# Tacko - School/College Bus Tracker

A real-time school bus tracking system built with **FastAPI** (Python) and **Vanilla JavaScript**. It enables students and parents to track buses on a map in real-time, allows drivers to broadcast their location efficiently, and provides a comprehensive admin panel for fleet management.

## 🚀 Features

- **Real-time Tracking**: Live location updates using **WebSockets** for low-latency communication.
- **Interactive Map**: Built with **Leaflet.js** featuring smooth marker animations and custom icons.
- **Role-Based Access Control (RBAC)**:
    - **Admin**: Full control to add/delete buses and register drivers.
    - **Driver**: Mobile-friendly interface to broadcast live GPS location.
    - **Student/Parent**: Read-only view to track allocated buses.
- **Simulation Logic**: Integrated background task to simulate bus movements for demonstration purposes.
- **Security**: JWT (JSON Web Token) authentication for secure API access.

## 🏗️ Built With

* **Languages:** Python 3.10+, JavaScript (ES6+), HTML5, CSS3
* **Frontend:** Vanilla JS, Leaflet.js (Maps)
* **Backend:** FastAPI, Uvicorn, WebSockets
* **Database:** SQLite
* **APIs & Tools:** OpenStreetMap (Tiles), Python-Jose (JWT), Passlib (Hashing)

## ⚙️ Installation & Setup

Follow these steps to get the project running locally.

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/tacko.git
cd tacko
```

### 2. Backend Setup
Navigate to the backend folder and install dependencies.

```bash
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Run the Application
Start the server using `uvicorn` or the main script. The backend serves the frontend static files automatically.

```bash
# Run using the python script
python main.py

# OR using uvicorn with hot-reload
uvicorn main:app --reload
```

Open your browser and navigate to: **http://localhost:8000**

## 📖 Usage Guide

### Default Credentials
Use the following pre-seeded accounts into the system:

| Role      | Username | Password     | Permissions                             |
|-----------|----------|--------------|-----------------------------------------|
| **Admin** | `admin`  | `admin123`   | Create/Delete Buses & Drivers, View Map |
| **Driver**| `driver` | `driver123`  | Broadcast Location, View Map            |
| **User**  | `student`| `student123` | View Map Only                           |

### Admin Dashboard
1. Log in as `admin`.
2. Use the **Admin Panel** on the left to:
   - Register new drivers.
   - Add new buses (assign a Bus ID and Route).
   - Delete existing buses.

### Driver Mode
1. Log in as `driver` (or a newly created driver).
2. Click **Start Tracking** to begin broadcasting your realtime location.
   - *Note: This requires the device to have GPS capabilities. If testing on localhost, the browser's geolocation is used.*

### Simulation
The system automatically starts a background simulation of two buses moving across predefined routes in Bangalore when the server starts. This allows you to verify the UI without physical drivers.

## 📂 Project Structure

```
tacko/
├── backend/
│   ├── main.py              # Application entry point, API routes, WebSocket manager
│   ├── database.py          # Database initialization, schemas, and CRUD operations
│   ├── simulate_movement.py # Logic for simulated bus movement (Demo mode)
│   ├── bus_tracker.db       # SQLite database file (Auto-generated)
│   └── requirements.txt     # Python dependencies
└── frontend/
    ├── index.html           # Main application entry point
    ├── style.css            # Application styling
    └── app.js               # Frontend logic, Auth, Map handling, WebSocket connection
```

## 📄 License

Distributed under the MIT License.
