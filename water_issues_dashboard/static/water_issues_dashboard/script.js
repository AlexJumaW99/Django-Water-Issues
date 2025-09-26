// Global variables
let map;
let municipalityData = null;
let incidentsData = null;
let parksData = null;
let currentLayers = {
    municipalities: null,
    wildfires: null,
    floods: null,
    parks: null
};

// Search + geolocation
let searchIndex = [];
let lastSearchResults = [];
let userMarker = null;
const userIcon = L.icon({
    iconUrl: 'data:image/svg+xml;base64,' + btoa('<svg xmlns="http://www.w3.org/2000/svg" width="25" height="25" viewBox="0 0 24 24" fill="#5f788a"><circle cx="12" cy="8" r="4"/><path d="M12 14c-6.67 0-8 2.33-8 4v2h16v-2c0-1.67-1.33-4-8-4z"/></svg>'),
    iconSize: [25, 25],
    iconAnchor: [12.5, 12.5],
    popupAnchor: [0, -13]
});

// Helper function to make CSRF-safe AJAX requests
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Helper function to load JSON data from Django API
async function loadJSONData(endpoint) {
    try {
        const response = await fetch(endpoint);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Error loading data from ${endpoint}:`, error);
        return null;
    }
}

// Helper function to get centroid of polygon
function getCentroid(coordinates) {
    let totalLat = 0;
    let totalLon = 0;
    let count = 0;
    
    // Handle nested arrays for polygon coordinates
    const coords = Array.isArray(coordinates[0][0]) ? coordinates[0] : coordinates;
    
    coords.forEach(coord => {
        totalLon += coord[0];
        totalLat += coord[1];
        count++;
    });
    
    return [totalLat / count, totalLon / count];
}

// Helper function to calculate bounds for a feature
function getFeatureBounds(feature) {
    const geometry = feature.geometry;
    let minLat = Infinity, maxLat = -Infinity;
    let minLng = Infinity, maxLng = -Infinity;

    function processCoords(coords, depth) {
        if (depth === 0) {
            // This is a coordinate pair [lng, lat]
            minLng = Math.min(minLng, coords[0]);
            maxLng = Math.max(maxLng, coords[0]);
            minLat = Math.min(minLat, coords[1]);
            maxLat = Math.max(maxLat, coords[1]);
        } else {
            // This is an array of coordinates
            coords.forEach(coord => processCoords(coord, depth - 1));
        }
    }

    if (geometry.type === 'Point') {
        const [lng, lat] = geometry.coordinates;
        return [[lat, lng], [lat, lng]];
    } else if (geometry.type === 'Polygon') {
        processCoords(geometry.coordinates, 2);
    } else if (geometry.type === 'MultiPolygon') {
        processCoords(geometry.coordinates, 3);
    }

    return [[minLat, minLng], [maxLat, maxLng]];
}

// Function to zoom to a specific feature
function zoomToFeature(feature, layer) {
    const bounds = getFeatureBounds(feature);
    
    // Add some padding to the bounds
    const padding = 0.01;
    const paddedBounds = [
        [bounds[0][0] - padding, bounds[0][1] - padding],
        [bounds[1][0] + padding, bounds[1][1] + padding]
    ];
    
    // Fit the map to the bounds with animation
    map.fitBounds(paddedBounds, {
        animate: true,
        duration: 1.5,
        easeLinearity: 0.25,
        padding: [20, 20]
    });
}

// Zoom to a point (for "Find me" and point results)
function zoomToPoint(lat, lng) {
    const padding = 0.01;
    const bounds = [[lat - padding, lng - padding], [lat + padding, lng + padding]];
    map.fitBounds(bounds, {
        animate: true,
        duration: 1.5,
        easeLinearity: 0.25,
        padding: [20, 20]
    });
}

// Initialize the application
async function initApp() {
    document.getElementById('dataStatus').textContent = 'Loading data from Django API...';
    
    // Load data from Django API
    const allData = await loadJSONData(apiBaseUrl);
    if (!allData) {
        console.warn('Could not load data from Django API');
        document.getElementById('dataStatus').textContent = 'Failed to load data';
        return;
    }
    
    municipalityData = allData.municipalities || { type: "FeatureCollection", features: [] };
    incidentsData = allData.incidents || { type: "FeatureCollection", features: [] };
    parksData = allData.parks || { type: "FeatureCollection", features: [] };
    
    document.getElementById('dataStatus').textContent = 'Data loaded from Django API';
    
    initMap();
    setupEventListeners();
    updateMap();
    updateMetrics();
    buildSearchIndex();
}

// Initialize the map
function initMap() {
    // Center on Manitoba
    map = L.map('map', {
        fullscreenControl: true,
        fullscreenControlOptions: {
            position: 'topleft',
            title: 'View Fullscreen',
            titleCancel: 'Exit Fullscreen',
        }
    }).setView([53.7609, -98.8139], 5);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
}

// Setup event listeners
function setupEventListeners() {
    // Municipality filters
    document.getElementById('statusCity').addEventListener('change', updateFiltersAndMap);
    document.getElementById('statusTown').addEventListener('change', updateFiltersAndMap);
    document.getElementById('statusRM').addEventListener('change', updateFiltersAndMap);
    
    // Population sliders
    document.getElementById('popMin').addEventListener('input', function() {
        document.getElementById('popMinValue').textContent = parseInt(this.value).toLocaleString();
        updateFiltersAndMap();
    });
    
    document.getElementById('popMax').addEventListener('input', function() {
        document.getElementById('popMaxValue').textContent = parseInt(this.value).toLocaleString();
        updateFiltersAndMap();
    });
    
    // Incident filters
    document.getElementById('showWildfires').addEventListener('change', updateFiltersAndMap);
    document.getElementById('showFloods').addEventListener('change', updateFiltersAndMap);
    document.getElementById('statusConfirmed').addEventListener('change', updateFiltersAndMap);
    document.getElementById('statusSuspected').addEventListener('change', updateFiltersAndMap);
    
    // Map display options
    document.getElementById('showParks').addEventListener('change', updateFiltersAndMap);

    // Find Me & search
    document.getElementById('findMeBtn').addEventListener('click', onFindMe);
    const searchInput = document.getElementById('searchInput');
    const clearBtn = document.getElementById('clearSearch');
    searchInput.addEventListener('input', onSearchInput);
    searchInput.addEventListener('keydown', onSearchKeydown);
    searchInput.addEventListener('focus', onSearchInput);
    clearBtn.addEventListener('click', () => {
        searchInput.value = '';
        hideSuggestions();
        clearBtn.style.display = 'none';
    });

    // Hide suggestions when clicking elsewhere
    document.addEventListener('click', (e) => {
        const wrap = document.querySelector('.search-wrapper');
        if (!wrap.contains(e.target)) hideSuggestions();
    });
}

// Update filters and map (for Django form integration)
function updateFiltersAndMap() {
    // Update URL with current filter state for Django
    const form = document.getElementById('filterForm');
    const formData = new FormData(form);
    const params = new URLSearchParams();
    
    // Add checkbox states
    params.set('statusCity', document.getElementById('statusCity').checked);
    params.set('statusTown', document.getElementById('statusTown').checked);
    params.set('statusRM', document.getElementById('statusRM').checked);
    params.set('showWildfires', document.getElementById('showWildfires').checked);
    params.set('showFloods', document.getElementById('showFloods').checked);
    params.set('statusConfirmed', document.getElementById('statusConfirmed').checked);
    params.set('statusSuspected', document.getElementById('statusSuspected').checked);
    params.set('showParks', document.getElementById('showParks').checked);
    
    // Add slider values
    params.set('popMin', document.getElementById('popMin').value);
    params.set('popMax', document.getElementById('popMax').value);
    
    // Update URL without refreshing page
    const newUrl = window.location.pathname + '?' + params.toString();
    window.history.replaceState({}, '', newUrl);
    
    // Update the map display
    updateMap();
}

// Update the map based on current filters
function updateMap() {
    // Clear existing layers
    Object.values(currentLayers).forEach(layer => {
        if (layer) map.removeLayer(layer);
    });

    // Get filter values
    const filters = {
        municipalities: {
            city: document.getElementById('statusCity').checked,
            town: document.getElementById('statusTown').checked,
            rm: document.getElementById('statusRM').checked,
            popMin: parseInt(document.getElementById('popMin').value),
            popMax: parseInt(document.getElementById('popMax').value)
        },
        incidents: {
            wildfires: document.getElementById('showWildfires').checked,
            floods: document.getElementById('showFloods').checked,
            confirmed: document.getElementById('statusConfirmed').checked,
            suspected: document.getElementById('statusSuspected').checked
        },
        display: {
            parks: document.getElementById('showParks').checked
        }
    };

    // Add parks if enabled
    if (filters.display.parks && parksData) {
        addParks();
    }

    // Add municipalities
    if (municipalityData) {
        addMunicipalities(filters.municipalities);
    }

    // Add incidents
    if (incidentsData) {
        addIncidents(filters.incidents);
    }

    // Update metrics
    updateMetrics();
}

// Add parks to map
function addParks() {
    const parksGroup = L.featureGroup();

    parksData.features.forEach(feature => {
        const props = feature.properties;
        const name = props.NAME_E || props.name || 'Unknown Park';
        
        const layer = L.geoJSON(feature, {
            style: {
                fillColor: '#228b22',
                fillOpacity: 0.3,
                weight: 1,
                color: '#0f5e0f',
                dashArray: '5, 5'
            }
        }).bindPopup(`
            <div style='font-family: Arial, sans-serif; width: 300px;'>
                <h4 style='color: #228b22; margin-bottom: 10px;'>🌲 ${name}</h4>
                <table style='width: 100%; border-spacing: 5px;'>
                    <tr><td><b>Province:</b></td><td>${props.LOC_E || 'N/A'}</td></tr>
                    <tr><td><b>Management:</b></td><td>${props.MGMT_E || 'N/A'}</td></tr>
                    <tr><td><b>Owner:</b></td><td>${props.OWNER_E || 'N/A'}</td></tr>
                    <tr><td><b>Park Class:</b></td><td>${props.PRK_CLSS || 'N/A'}</td></tr>
                    ${props.URL ? `<tr><td colspan='2'><a href='${props.URL}' target='_blank'>🔗 Visit Park Website</a></td></tr>` : ''}
                </table>
                <a href="#" class="zoom-link" onclick="zoomToFeature(${JSON.stringify(feature).replace(/"/g, '&quot;')}, this); return false;">
                    🔍 Take a Closer Look
                </a>
            </div>
        `);
        
        parksGroup.addLayer(layer);
    });

    if (parksData.features.length > 0) {
        currentLayers.parks = parksGroup.addTo(map);
    }
}

// Add municipalities to map
function addMunicipalities(filters) {
    const municipalityGroup = L.featureGroup();
    let selectedCount = 0;

    municipalityData.features.forEach(feature => {
        const props = feature.properties;
        const status = (props.status || '').toLowerCase();
        const population = props.population_2021 || 0;

        // Check filters
        let passesFilter = false;
        if (status === 'city' && filters.city) passesFilter = true;
        if (status === 'town' && filters.town) passesFilter = true;
        if ((status.includes('rural') || status === 'rm') && filters.rm) passesFilter = true;

        if (passesFilter && population >= filters.popMin && population <= filters.popMax) {
            const color = status === 'city' ? '#3b82f6' : status === 'town' ? '#10b981' : '#64748b';
            
            // Create emoji based on status
            const emoji = status === 'city' ? '🏙️' : status === 'town' ? '🏘️' : '🌾';
            const displayStatus = status === 'city' ? 'City of' : status === 'town' ? 'Town of' : 'RM of';
            
            const layer = L.geoJSON(feature, {
                style: {
                    fillColor: color,
                    fillOpacity: 0.1,
                    weight: 1,
                    color: color
                }
            }).bindPopup(`
                <div style='font-family: Arial, sans-serif;'>
                    <h4>${emoji} ${displayStatus} ${props.name}</h4>
                    <table style='border-spacing: 5px;'>
                        <tr><td><b>Status:</b></td><td>${props.status}</td></tr>
                        <tr><td><b>Population (2021):</b></td><td>${population.toLocaleString()}</td></tr>
                    </table>
                    <a href="#" class="zoom-link" onclick="zoomToFeature(${JSON.stringify(feature).replace(/"/g, '&quot;')}, this); return false;">
                        🔍 Take a Closer Look
                    </a>
                </div>
            `);
            
            municipalityGroup.addLayer(layer);
            selectedCount++;
        }
    });

    document.getElementById('selectedPlaces').textContent = selectedCount;
    
    if (selectedCount > 0) {
        currentLayers.municipalities = municipalityGroup.addTo(map);
    }
}

// Add incidents to map
function addIncidents(filters) {
    const wildfireGroup = L.featureGroup();
    const floodGroup = L.featureGroup();

    incidentsData.features.forEach(feature => {
        const props = feature.properties;
        const type = props.type;
        const status = props.status || props.confidence;

        // Check status filter
        if (status === 'confirmed' && !filters.confirmed) return;
        if (status === 'suspected' && !filters.suspected) return;

        // Get centroid for marker placement
        let centerLat, centerLng;
        if (feature.geometry.type === 'Polygon') {
            [centerLat, centerLng] = getCentroid(feature.geometry.coordinates);
        } else if (feature.geometry.type === 'MultiPolygon') {
            // Use the first polygon's centroid
            [centerLat, centerLng] = getCentroid(feature.geometry.coordinates[0]);
        } else if (feature.geometry.type === 'Point') {
            [centerLng, centerLat] = feature.geometry.coordinates;
        } else {
            return; // Skip unsupported geometry types
        }

        if (type === 'wildfire' && filters.wildfires) {
            // Add wildfire polygon
            const fillColor = status === 'confirmed' ? '#d73027' : '#fc8d59';
            
            if (feature.geometry.type !== 'Point') {
                L.geoJSON(feature, {
                    style: {
                        color: fillColor,
                        weight: 2,
                        fillColor: fillColor,
                        fillOpacity: 0.2
                    }
                }).addTo(wildfireGroup);
            }

            // Add wildfire marker
            const icon = L.divIcon({
                html: '<i class="fas fa-fire" style="color: ' + (status === 'confirmed' ? 'red' : 'orange') + ';"></i>',
                iconSize: [20, 20],
                className: 'custom-div-icon'
            });

            L.marker([centerLat, centerLng], { icon: icon })
                .bindPopup(`
                    <div style='font-family: Arial, sans-serif;'>
                        <strong>${props.name}</strong><br>
                        Type: Wildfire<br>
                        Status: ${status}<br>
                        Started: ${props.started_at || 'Unknown'}<br>
                        ${props.description || ''}
                        <a href="#" class="zoom-link" onclick="zoomToFeature(${JSON.stringify(feature).replace(/"/g, '&quot;')}, this); return false;">
                            🔍 Take a Closer Look
                        </a>
                    </div>
                `)
                .addTo(wildfireGroup);
        }

        if (type === 'flood' && filters.floods) {
            // Add flood polygon
            const fillColor = status === 'confirmed' ? '#2c7fb8' : '#7fcdbb';
            
            if (feature.geometry.type !== 'Point') {
                L.geoJSON(feature, {
                    style: {
                        color: fillColor,
                        weight: 2,
                        fillColor: fillColor,
                        fillOpacity: 0.2
                    }
                }).addTo(floodGroup);
            }

            // Add flood marker
            const icon = L.divIcon({
                html: '<i class="fas fa-tint" style="color: ' + (status === 'confirmed' ? 'blue' : 'lightblue') + ';"></i>',
                iconSize: [20, 20],
                className: 'custom-div-icon'
            });

            L.marker([centerLat, centerLng], { icon: icon })
                .bindPopup(`
                    <div style='font-family: Arial, sans-serif;'>
                        <strong>${props.name}</strong><br>
                        Type: Flood<br>
                        Status: ${status}<br>
                        Started: ${props.started_at || 'Unknown'}<br>
                        ${props.description || ''}
                        <a href="#" class="zoom-link" onclick="zoomToFeature(${JSON.stringify(feature).replace(/"/g, '&quot;')}, this); return false;">
                            🔍 Take a Closer Look
                        </a>
                    </div>
                `)
                .addTo(floodGroup);
        }
    });

    if (wildfireGroup.getLayers().length > 0) {
        currentLayers.wildfires = wildfireGroup.addTo(map);
    }

    if (floodGroup.getLayers().length > 0) {
        currentLayers.floods = floodGroup.addTo(map);
    }
}

// Update metrics display
function updateMetrics() {
    // Get filter states
    const showWildfires = document.getElementById('showWildfires').checked;
    const showFloods = document.getElementById('showFloods').checked;
    const statusConfirmed = document.getElementById('statusConfirmed').checked;
    const statusSuspected = document.getElementById('statusSuspected').checked;
    const showParks = document.getElementById('showParks').checked;

    // Calculate municipalities count
    let muniCount = 0;
    let totalPop = 0;
    
    if (municipalityData) {
        const filters = {
            city: document.getElementById('statusCity').checked,
            town: document.getElementById('statusTown').checked,
            rm: document.getElementById('statusRM').checked,
            popMin: parseInt(document.getElementById('popMin').value),
            popMax: parseInt(document.getElementById('popMax').value)
        };

        municipalityData.features.forEach(feature => {
            const props = feature.properties;
            const status = (props.status || '').toLowerCase();
            const population = props.population_2021 || 0;

            let passesFilter = false;
            if (status === 'city' && filters.city) passesFilter = true;
            if (status === 'town' && filters.town) passesFilter = true;
            if ((status.includes('rural') || status === 'rm') && filters.rm) passesFilter = true;

            if (passesFilter && population >= filters.popMin && population <= filters.popMax) {
                muniCount++;
                totalPop += population;
            }
        });
    }

    // Calculate incidents count
    let fireCount = 0;
    let floodCount = 0;

    if (incidentsData) {
        incidentsData.features.forEach(feature => {
            const props = feature.properties;
            const type = props.type;
            const status = props.status || props.confidence;

            if ((status === 'confirmed' && statusConfirmed) || 
                (status === 'suspected' && statusSuspected)) {
                if (type === 'wildfire' && showWildfires) fireCount++;
                if (type === 'flood' && showFloods) floodCount++;
            }
        });
    }

    // Calculate parks count
    let parkCount = 0;
    if (showParks && parksData) {
        parkCount = parksData.features.length;
    }

    // Update display
    document.getElementById('muniCount').textContent = muniCount;
    document.getElementById('popCount').textContent = totalPop.toLocaleString();
    document.getElementById('fireCount').textContent = fireCount;
    document.getElementById('floodCount').textContent = floodCount;
    document.getElementById('parkCount').textContent = parkCount;
    
    // Update total incidents
    document.getElementById('totalIncidents').textContent = incidentsData ? incidentsData.features.length : 0;
}

// Switch tabs
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.closest('.tab').classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    if (tabName === 'home') {
        document.getElementById('homeTab').classList.add('active');
        // Refresh search suggestions if there's a query
        onSearchInput();
    } else if (tabName === 'report') {
        document.getElementById('reportTab').classList.add('active');
        updateDataSummary();
    }
}

// File upload handlers
function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        processFile(files[0]);
    }
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        processFile(files[0]);
    }
}

function processFile(file) {
    const reader = new FileReader();
    
    reader.onload = function(e) {
        try {
            const data = JSON.parse(e.target.result);
            uploadFileToServer(file, data);
        } catch (error) {
            showError('Failed to parse JSON file: ' + error.message);
        }
    };
    
    reader.readAsText(file);
}

function uploadFileToServer(file, data) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));

    fetch(uploadUrl, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showUploadResult(result);
            // Reload data from server
            reloadDataFromServer();
        } else {
            showError(result.message || 'Upload failed');
        }
    })
    .catch(error => {
        showError('Upload failed: ' + error.message);
    });
}

async function reloadDataFromServer() {
    // Reload data from Django API
    const allData = await loadJSONData(apiBaseUrl);
    if (allData) {
        municipalityData = allData.municipalities;
        incidentsData = allData.incidents;
        parksData = allData.parks;
        
        updateMap();
        updateMetrics();
        updateDataSummary();
        buildSearchIndex();
        
        // Refresh search if there's a query
        const searchInput = document.getElementById('searchInput');
        if (searchInput.value.trim()) onSearchInput();
    }
}

function showUploadResult(result) {
    const resultDiv = document.getElementById('uploadResult');
    resultDiv.innerHTML = `
        <div class="alert alert-success">
            <h4>✅ Upload Successful!</h4>
            <div style="margin-top: 10px;">
                <strong>New incidents added:</strong> ${result.added}<br>
                <strong>Duplicates skipped:</strong> ${result.duplicates}<br>
                <strong>Total incidents now:</strong> ${result.total}
            </div>
        </div>
    `;
    
    // Update data status
    document.getElementById('dataStatus').textContent = 'Using data with uploads';
}

function showError(message) {
    const resultDiv = document.getElementById('uploadResult');
    resultDiv.innerHTML = `
        <div class="alert alert-danger">
            <h4>❌ Upload Failed</h4>
            <p>${message}</p>
        </div>
    `;
}

async function resetToDefault() {
    if (confirm('Are you sure you want to reload data from the server? This will refresh all data.')) {
        document.getElementById('dataStatus').textContent = 'Reloading data...';
        
        // Clear upload results
        document.getElementById('uploadResult').innerHTML = '';
        
        // Reload from server
        await reloadDataFromServer();
        
        document.getElementById('dataStatus').textContent = 'Data reloaded from Django API';
    }
}

function updateDataSummary() {
    const summaryDiv = document.getElementById('dataSummary');
    
    if (!incidentsData || !incidentsData.features) {
        summaryDiv.innerHTML = '<p>No incident data available</p>';
        return;
    }

    // Count by type and status
    const typeCounts = { wildfire: 0, flood: 0 };
    const statusCounts = { confirmed: 0, suspected: 0 };
    
    incidentsData.features.forEach(feature => {
        const props = feature.properties;
        
        // Count by type
        if (props.type) {
            typeCounts[props.type] = (typeCounts[props.type] || 0) + 1;
        }
        
        // Count by status
        const status = props.status || props.confidence;
        if (status) {
            statusCounts[status] = (statusCounts[status] || 0) + 1;
        }
    });

    let html = `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <h4>By Type:</h4>
                <ul style="list-style: none; padding: 0;">
                    <li>🔥 Wildfire: ${typeCounts.wildfire || 0}</li>
                    <li>💧 Flood: ${typeCounts.flood || 0}</li>
                </ul>
            </div>
            <div>
                <h4>By Status:</h4>
                <ul style="list-style: none; padding: 0;">
                    <li>✅ Confirmed: ${statusCounts.confirmed || 0}</li>
                    <li>⚠️ Suspected: ${statusCounts.suspected || 0}</li>
                </ul>
            </div>
        </div>
    `;
    
    // Add sample data table
    html += `
        <h4 style="margin-top: 20px;">Sample Data:</h4>
        <table class="summary-table">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Started</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    const sampleFeatures = incidentsData.features.slice(0, 5);
    if (sampleFeatures.length === 0) {
        html += '<tr><td colspan="4">No incidents found</td></tr>';
    } else {
        sampleFeatures.forEach(feature => {
            const props = feature.properties;
            const status = props.status || props.confidence;
            html += `
                <tr>
                    <td>${props.name || 'N/A'}</td>
                    <td>${props.type || 'N/A'}</td>
                    <td>${status || 'N/A'}</td>
                    <td>${props.started_at || 'N/A'}</td>
                </tr>
            `;
        });
    }
    
    html += `
            </tbody>
        </table>
    `;
    
    if (incidentsData.features.length > 5) {
        html += `<p style="color: #666; font-size: 0.9em;">Showing first 5 of ${incidentsData.features.length} incidents</p>`;
    }
    
    summaryDiv.innerHTML = html;
}

function downloadExampleData() {
    const exampleData = {
        type: "FeatureCollection",
        features: [
            {
                type: "Feature",
                geometry: {
                    type: "Polygon",
                    coordinates: [[
                        [-97.2, 49.9],
                        [-97.1, 49.9],
                        [-97.1, 49.8],
                        [-97.2, 49.8],
                        [-97.2, 49.9]
                    ]]
                },
                properties: {
                    name: "Example Wildfire",
                    type: "wildfire",
                    status: "confirmed",
                    started_at: "2024-03-15",
                    description: "Example wildfire incident near Winnipeg"
                }
            },
            {
                type: "Feature",
                geometry: {
                    type: "Polygon",
                    coordinates: [[
                        [-98.5, 53.5],
                        [-98.4, 53.5],
                        [-98.4, 53.4],
                        [-98.5, 53.4],
                        [-98.5, 53.5]
                    ]]
                },
                properties: {
                    name: "Example Flood",
                    type: "flood",
                    status: "suspected",
                    started_at: "2024-04-01",
                    description: "Example flood incident in northern Manitoba"
                }
            }
        ]
    };

    const dataStr = JSON.stringify(exampleData, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
    
    const link = document.createElement('a');
    link.setAttribute('href', dataUri);
    link.setAttribute('download', 'example_incidents.geojson');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/* -------------------- Search & Find Me logic -------------------- */

function buildSearchIndex() {
    const index = [];

    // Municipalities
    if (municipalityData && municipalityData.features) {
        municipalityData.features.forEach(feature => {
            const p = feature.properties || {};
            const status = (p.status || '').toLowerCase();
            let prefix = 'RM of';
            if (status === 'city') prefix = 'City of';
            else if (status === 'town') prefix = 'Town of';

            const label = `${prefix} ${p.name} MB`;
            index.push({
                label,
                labelLower: label.toLowerCase(),
                type: status === 'rm' ? 'RM' : (status.charAt(0).toUpperCase() + status.slice(1)),
                feature
            });
        });
    }

    // Parks
    if (parksData && parksData.features) {
        parksData.features.forEach(feature => {
            const p = feature.properties || {};
            const name = p.NAME_E || p.name || 'Unnamed Park';
            const label = `${name} (Park)`;
            index.push({
                label,
                labelLower: label.toLowerCase(),
                type: 'Park',
                feature
            });
        });
    }

    // Incidents
    if (incidentsData && incidentsData.features) {
        incidentsData.features.forEach(feature => {
            const p = feature.properties || {};
            const t = (p.type || '').toLowerCase();
            const label = `${p.name} (${t === 'wildfire' ? 'Wildfire' : 'Flood'})`;
            index.push({
                label,
                labelLower: label.toLowerCase(),
                type: t === 'wildfire' ? 'Wildfire' : 'Flood',
                feature
            });
        });
    }

    // Sort alphabetically
    index.sort((a, b) => a.label.localeCompare(b.label));

    searchIndex = index;
}

function onSearchInput() {
    const input = document.getElementById('searchInput');
    const clearBtn = document.getElementById('clearSearch');
    const q = input.value.trim().toLowerCase();
    if (!q) { hideSuggestions(); clearBtn.style.display = 'none'; return; }
    clearBtn.style.display = 'block';

    // Rank results: startsWith first, then includes
    const starts = [];
    const includes = [];
    for (const item of searchIndex) {
        const idx = item.labelLower.indexOf(q);
        if (idx === 0) starts.push(item);
        else if (idx > 0) includes.push(item);
    }
    lastSearchResults = [...starts, ...includes].slice(0, 12);
    renderSuggestions(lastSearchResults, q);
}

function renderSuggestions(results, q) {
    const list = document.getElementById('suggestions');
    if (!results.length) { hideSuggestions(); return; }
    list.innerHTML = results.map((r, i) => {
        return `
            <div class="suggestion-item" data-idx="${i}">
                <span>${highlightMatch(r.label, q)}</span>
                <span class="suggestion-type">${r.type}</span>
            </div>
        `;
    }).join('');
    list.style.display = 'block';

    // Click handler
    list.querySelectorAll('.suggestion-item').forEach(el => {
        el.addEventListener('click', () => {
            const idx = parseInt(el.getAttribute('data-idx'), 10);
            selectSearchResult(results[idx]);
        });
    });
}

function hideSuggestions() {
    const list = document.getElementById('suggestions');
    list.style.display = 'none';
    list.innerHTML = '';
}

function onSearchKeydown(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        if (lastSearchResults.length > 0) {
            selectSearchResult(lastSearchResults[0]);
        }
    } else if (e.key === 'Escape') {
        hideSuggestions();
        document.getElementById('searchInput').blur();
    }
}

function selectSearchResult(item) {
    hideSuggestions();
    document.getElementById('searchInput').blur();
    zoomToFeature(item.feature);
}

function highlightMatch(text, q) {
    const idx = text.toLowerCase().indexOf(q);
    if (idx < 0) return text;
    const before = text.slice(0, idx);
    const match = text.slice(idx, idx + q.length);
    const after = text.slice(idx + q.length);
    return `${before}<strong>${match}</strong>${after}`;
}

function onFindMe() {
    if (!('geolocation' in navigator)) {
        alert('Geolocation is not supported by your browser.');
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (pos) => {
            const { latitude, longitude, accuracy } = pos.coords;

            // Remove previous marker if any
            if (userMarker) {
                map.removeLayer(userMarker);
                userMarker = null;
            }

            userMarker = L.marker([latitude, longitude], { icon: userIcon })
                .addTo(map)
                .bindPopup(`You are here<br><small>Accuracy ±${Math.round(accuracy)} m</small>`);
            userMarker.openPopup();

            zoomToPoint(latitude, longitude);
        },
        (err) => {
            console.error(err);
            alert('Unable to get your location. Please ensure permissions are granted.');
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', initApp);