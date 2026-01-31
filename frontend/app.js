const loginOverlay = document.getElementById('login-overlay');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const appContainer = document.getElementById('app-container');
const userInfo = document.getElementById('user-info');
const logoutBtn = document.getElementById('logout-btn');

// Admin Elements
const adminPanel = document.getElementById('admin-panel');
const addDriverForm = document.getElementById('add-driver-form');
const addBusForm = document.getElementById('add-bus-form');
const driverSelect = document.getElementById('driver-select');

// Driver Elements
const driverDashboard = document.getElementById('driver-dashboard');
const startTrackingBtn = document.getElementById('start-tracking-btn');
const stopTrackingBtn = document.getElementById('stop-tracking-btn');
const trackingStatus = document.getElementById('tracking-status');

let map = null;
let socket = null;
let busMarkers = {};
let watchId = null;

// --- AUTH LOGIC ---

loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    try {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch('/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error('Login failed');
        }

        const data = await response.json();
        handleLoginSuccess(data.access_token, data.role, username);
    } catch (err) {
        loginError.textContent = "Invalid username or password";
    }
});

function handleLoginSuccess(token, role, username) {
    localStorage.setItem('token', token);
    localStorage.setItem('role', role);
    localStorage.setItem('username', username);

    showApp(username, role);
}

async function showApp(username, role) {
    loginOverlay.style.display = 'none';
    appContainer.style.display = 'flex';
    userInfo.textContent = `Logged in as: ${username} (${role})`;

    // Show Panel based on Role
    if (role === 'admin') {
        adminPanel.style.display = 'block';
        await loadDrivers(); // Populate dropdown
    } else if (role === 'driver') {
        driverDashboard.style.display = 'block';
    }

    initMap();
    fetchInitialBuses(); // Load roster immediately
    connectWebSocket();
}

logoutBtn.addEventListener('click', () => {
    stopTracking(); // Ensure tracking stops on logout
    localStorage.clear();
    location.reload();
});

// Check if already logged in
// Check if already logged in
const savedToken = localStorage.getItem('token');
if (savedToken) {
    verifyToken(savedToken);
}

async function verifyToken(token) {
    try {
        const res = await fetch('/users/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            const user = await res.json();
            // Update role/username in case they changed on server
            localStorage.setItem('role', user.role);
            localStorage.setItem('username', user.username);
            showApp(user.username, user.role);
        } else {
            // Token invalid or expired
            console.log("Token invalid, logging out...");
            localStorage.clear();
            // Login overlay is already visible by default, app-container hidden
        }
    } catch (e) {
        console.error("Token verification failed", e);
        localStorage.clear();
    }
}

// --- ADMIN LOGIC ---

async function loadDrivers() {
    const token = localStorage.getItem('token');
    try {
        const res = await fetch('/drivers', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const drivers = await res.json();

        driverSelect.innerHTML = '<option value="">Select Driver</option>';
        drivers.forEach(driver => {
            const opt = document.createElement('option');
            opt.value = driver;
            opt.textContent = driver;
            driverSelect.appendChild(opt);
        });
    } catch (e) {
        console.error("Failed to load drivers", e);
    }
}

addDriverForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('new-driver-user').value;
    const password = document.getElementById('new-driver-pass').value;
    const token = localStorage.getItem('token');

    try {
        const res = await fetch('/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ username, password })
        });

        if (res.ok) {
            alert('Driver added!');
            addDriverForm.reset();
            loadDrivers();
        } else {
            alert('Failed to add driver');
        }
    } catch (e) { console.error(e); }
});

addBusForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const bus_id = document.getElementById('bus-id').value;
    const route_stops = document.getElementById('route-stops').value;
    const driver_name = driverSelect.value;
    const token = localStorage.getItem('token');

    try {
        const res = await fetch('/buses', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ bus_id, driver_name, route_stops })
        });

        if (res.ok) {
            alert('Bus added!');
            addBusForm.reset();
            // Update local state and UI immediately
            if (!busesData[bus_id]) {
                busesData[bus_id] = { bus_id, driver_name, route_stops };
                renderBusList();
            }
        } else {
            alert('Failed to add bus');
        }
    } catch (e) { console.error(e); }
});

// --- DRIVER TRACKING LOGIC ---

startTrackingBtn.addEventListener('click', () => {
    if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser");
        return;
    }

    startTrackingBtn.disabled = true;
    stopTrackingBtn.disabled = false;
    trackingStatus.textContent = "Status: Sending Updates...";
    trackingStatus.style.color = "green";

    const busId = prompt("Enter Bus ID checking out (e.g. KA-01-1234):", "KA-01-1234");

    watchId = navigator.geolocation.watchPosition((position) => {
        const { latitude, longitude } = position.coords;
        const payload = {
            bus_id: busId,
            lat: latitude,
            lon: longitude,
            route: "Active Route" // Ideally fetched from assignment
        };

        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(payload));
        }
    }, (error) => {
        console.error("Geo Error", error);
        alert("Error getting location: " + error.message);
        stopTracking();
    }, {
        enableHighAccuracy: true,
        maximumAge: 0,
        timeout: 5000
    });
});

function stopTracking() {
    if (watchId !== null) {
        navigator.geolocation.clearWatch(watchId);
        watchId = null;
    }
    startTrackingBtn.disabled = false;
    stopTrackingBtn.disabled = true;
    trackingStatus.textContent = "Status: Idle";
    trackingStatus.style.color = "black";
}

stopTrackingBtn.addEventListener('click', stopTracking);



let busesData = {}; // Store bus state: { bus_id: { ...bus_object, lat, lon } }
let busAnimations = {}; // { bus_id: { startLatLng, targetLatLng, startTime, duration } }

function initMap() {
    if (map) return;

    map = L.map('map').setView([12.9716, 77.5946], 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap'
    }).addTo(map);

    // Start Animation Loop
    requestAnimationFrame(animateMarkers);
}

// Custom Bus Icon
const busIcon = L.divIcon({
    className: 'custom-bus-icon',
    html: '<div style="background-color: #4285F4; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3); font-size: 14px;">🚌</div>',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12]
});

async function fetchInitialBuses() {
    try {
        console.log("Fetching initial buses...");
        const res = await fetch('/buses');
        const buses = await res.json();

        buses.forEach(bus => {
            if (!busesData[bus.bus_id]) {
                busesData[bus.bus_id] = { ...bus };
            }
        });
        renderBusList();
    } catch (e) {
        console.error("Error loading initial buses:", e);
    }
}

function connectWebSocket() {
    if (socket) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/locations`;

    socket = new WebSocket(wsUrl);

    socket.onopen = () => console.log("Connected to WebSocket");

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (Array.isArray(data)) {
            data.forEach(update => handleLocationUpdate(update));
        } else {
            handleLocationUpdate(data);
        }
    };

    socket.onclose = () => console.log("WebSocket Disconnected");
}

function handleLocationUpdate(update) {
    const { bus_id, lat, lon, route } = update;

    // Merge into store
    if (!busesData[bus_id]) {
        busesData[bus_id] = { bus_id, route_stops: route || 'Unknown' };
    }

    busesData[bus_id].lat = lat;
    busesData[bus_id].lon = lon;
    busesData[bus_id].lastUpdated = new Date();

    updateMapMarker(bus_id, lat, lon, busesData[bus_id].route_stops);
    renderBusList();
}

function updateMapMarker(busId, lat, lon, routeInfo) {
    // If marker exists, animate to new position
    if (busMarkers[busId]) {
        const startLatLng = busMarkers[busId].getLatLng();
        const targetLatLng = L.latLng(lat, lon);

        // Setup animation
        busAnimations[busId] = {
            startLatLng: startLatLng,
            targetLatLng: targetLatLng,
            startTime: performance.now(),
            duration: 1000 // Assume 1 second between updates for smooth glide
        };

        busMarkers[busId].setPopupContent(`<b>${busId}</b><br>${routeInfo}`);
    } else {
        // Create new marker immediately
        const marker = L.marker([lat, lon], { icon: busIcon }).addTo(map)
            .bindPopup(`<b>${busId}</b><br>${routeInfo}`);
        busMarkers[busId] = marker;
    }
}

function animateMarkers(time) {
    Object.keys(busAnimations).forEach(busId => {
        const anim = busAnimations[busId];
        if (!anim) return;

        const elapsed = time - anim.startTime;
        // Calculate progress (0 to 1)
        let progress = elapsed / anim.duration;

        if (progress > 1) {
            progress = 1;
            // Keep it at target until next update
        }

        // Linear interpolation
        const currentLat = anim.startLatLng.lat + (anim.targetLatLng.lat - anim.startLatLng.lat) * progress;
        const currentLng = anim.startLatLng.lng + (anim.targetLatLng.lng - anim.startLatLng.lng) * progress;

        if (busMarkers[busId]) {
            busMarkers[busId].setLatLng([currentLat, currentLng]);
        }

        if (progress === 1) {
            delete busAnimations[busId];
        }
    });

    requestAnimationFrame(animateMarkers);
}

function renderBusList() {
    const busList = document.getElementById('bus-list');
    if (!busList) return;

    busList.innerHTML = '<h3>Available Buses</h3>';

    if (Object.keys(busesData).length === 0) {
        busList.innerHTML += '<p>No buses found.</p>';
        return;
    }

    const role = localStorage.getItem('role');
    console.log("Current User Role:", role); // Debugging log

    Object.values(busesData).forEach(bus => {
        const item = document.createElement('div');
        item.className = 'bus-item';

        // Determine status based on if we have location data
        const isLive = bus.lat !== undefined;
        const statusColor = isLive ? 'green' : 'grey';
        const locationText = isLive
            ? `Loc: ${bus.lat.toFixed(4)}, ${bus.lon.toFixed(4)}`
            : '<i>Offline / No Data</i>';

        let deleteBtnHtml = '';
        if (role === 'admin') {
            deleteBtnHtml = `<button class="delete-bus-btn" data-bus-id="${bus.bus_id}" style="margin-left: 10px; background: #e74c3c; color: white; border: none; padding: 2px 6px; border-radius: 4px; cursor: pointer; font-size: 0.8em;">Delete</button>`;
        }

        item.innerHTML = `
            <div style="border-left: 4px solid ${statusColor}; padding-left: 8px; margin-bottom: 10px; background: #f9f9f9; padding: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <strong>${bus.bus_id}</strong>
                        <div style="font-size: 0.9em; color: #666;">Route: ${bus.route_stops || 'N/A'}</div>
                        <div style="font-size: 0.85em; margin-top: 4px;">${locationText}</div>
                    </div>
                    ${deleteBtnHtml}
                </div>
            </div>
        `;
        busList.appendChild(item);
    });

    // Add event listeners for delete buttons
    if (role === 'admin') {
        const buttons = busList.querySelectorAll('.delete-bus-btn');
        buttons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const busId = e.target.getAttribute('data-bus-id');
                deleteBus(busId);
            });
        });
    }
}

async function deleteBus(busId) {
    if (!confirm(`Are you sure you want to delete bus ${busId}?`)) return;

    const token = localStorage.getItem('token');
    try {
        const res = await fetch(`/buses/${busId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (res.ok) {
            alert('Bus deleted!');
            delete busesData[busId]; // Remove from local state
            if (busMarkers[busId]) {
                map.removeLayer(busMarkers[busId]); // Remove from map
                delete busMarkers[busId];
            }
            renderBusList(); // Re-render list
        } else {
            alert('Failed to delete bus');
        }
    } catch (e) {
        console.error("Error deleting bus:", e);
        alert('Error communicating with server');
    }
}
