/**
 * Immersive District Map View
 * 
 * This script provides an interactive, immersive map view for tax districts
 * with 3D-styled modern UI elements, district filtering, and interactive cards.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize map variable
    let map;
    let markers = [];
    let polygons = [];
    let activeInfoWindow = null;
    let activeDistrictId = null;
    let currentFilters = [];
    let bounds;
    
    // Initialize map with default center (will be adjusted based on districts)
    function initMap() {
        // Default center (Benton County, Washington approximate center)
        const defaultCenter = { lat: 46.25, lng: -119.25 };
        
        // Map styling for a modern, clean look
        const mapStyles = [
            {
                "featureType": "administrative",
                "elementType": "labels.text.fill",
                "stylers": [{"color": "#444444"}]
            },
            {
                "featureType": "landscape",
                "elementType": "all",
                "stylers": [{"color": "#f2f2f2"}]
            },
            {
                "featureType": "poi",
                "elementType": "all",
                "stylers": [{"visibility": "off"}]
            },
            {
                "featureType": "road",
                "elementType": "all",
                "stylers": [{"saturation": -100}, {"lightness": 45}]
            },
            {
                "featureType": "road.highway",
                "elementType": "all",
                "stylers": [{"visibility": "simplified"}]
            },
            {
                "featureType": "road.arterial",
                "elementType": "labels.icon",
                "stylers": [{"visibility": "off"}]
            },
            {
                "featureType": "transit",
                "elementType": "all",
                "stylers": [{"visibility": "off"}]
            },
            {
                "featureType": "water",
                "elementType": "all",
                "stylers": [{"color": "#c4eaf9"}, {"visibility": "on"}]
            }
        ];
        
        // Create map
        map = new google.maps.Map(document.getElementById('map'), {
            center: defaultCenter,
            zoom: 10,
            mapTypeId: 'roadmap',
            mapTypeControl: false,
            fullscreenControl: false,
            streetViewControl: false,
            styles: mapStyles,
            zoomControlOptions: {
                position: google.maps.ControlPosition.RIGHT_CENTER
            }
        });
        
        // Set bounds for the map
        bounds = new google.maps.LatLngBounds();
        
        // Add districts to the map
        addDistrictsToMap();
        
        // Add event listener for map click to close info panel
        map.addListener('click', function() {
            closeInfoPanel();
        });
        
        // Setup UI interactions
        setupUIInteractions();
    }
    
    // Generate random coordinates within Benton County area
    // This is a demo function - in a real app, you would get actual coordinates from database
    function generateRandomCoordinates(index) {
        // Benton County approximate bounds
        const minLat = 46.0;
        const maxLat = 46.5;
        const minLng = -119.6;
        const maxLng = -119.0;
        
        // Use the index to distribute points more evenly
        const lat = minLat + (maxLat - minLat) * (0.2 + 0.6 * Math.sin(index * 0.5));
        const lng = minLng + (maxLng - minLng) * (0.2 + 0.6 * Math.cos(index * 0.5));
        
        return { lat, lng };
    }
    
    // Generate polygon coordinates for a district
    // This is a demo function - in a real app, you would get actual boundary coordinates from database
    function generateDistrictPolygon(centerLat, centerLng, districtType) {
        const points = [];
        const sides = 5 + Math.floor(Math.random() * 6); // 5-10 sides
        const radius = 0.03 + (Math.random() * 0.07); // Random radius between 0.03-0.1 degrees
        
        // Adjust radius based on district type (for visual variety)
        let adjustedRadius = radius;
        if (districtType === 'SCHOOL') adjustedRadius = radius * 1.5;
        if (districtType === 'CITY') adjustedRadius = radius * 1.3;
        if (districtType === 'FIRE') adjustedRadius = radius * 1.2;
        
        // Create irregular polygon points
        for (let i = 0; i < sides; i++) {
            const angle = (i / sides) * 2 * Math.PI;
            const jitter = 0.7 + (Math.random() * 0.6); // Random between 0.7-1.3
            const lat = centerLat + (Math.sin(angle) * adjustedRadius * jitter);
            const lng = centerLng + (Math.cos(angle) * adjustedRadius * jitter);
            points.push({ lat, lng });
        }
        
        return points;
    }
    
    // Add districts to the map
    function addDistrictsToMap() {
        if (!districtsData || districtsData.length === 0) {
            console.error('No district data available');
            return;
        }
        
        // Clear existing markers and polygons
        markers.forEach(marker => marker.setMap(null));
        markers = [];
        
        polygons.forEach(polygon => polygon.setMap(null));
        polygons = [];
        
        // Add districts with polygons and markers
        districtsData.forEach((district, index) => {
            // Generate random coordinates for demo purposes
            const position = generateRandomCoordinates(index);
            district.latitude = position.lat;
            district.longitude = position.lng;
            
            // Generate polygon for this district
            const polygonCoords = generateDistrictPolygon(
                district.latitude, 
                district.longitude,
                district.district_type
            );
            district.polygonCoords = polygonCoords;
            
            // Create polygon for this district
            const polygon = createDistrictPolygon(district);
            if (polygon) {
                polygons.push(polygon);
            }
            
            // Create marker with custom styling based on district type
            const marker = createDistrictMarker(district);
            markers.push(marker);
            
            // Extend bounds to include this marker
            bounds.extend(new google.maps.LatLng(district.latitude, district.longitude));
        });
        
        // Fit map to bounds
        map.fitBounds(bounds);
        
        // Add district cards to carousel
        populateDistrictCarousel();
    }
    
    // Create polygon for a district
    function createDistrictPolygon(district) {
        if (!district.polygonCoords || district.polygonCoords.length < 3) {
            return null;
        }
        
        const districtType = district.district_type || 'OTHER';
        let fillColor = '#7E57C2'; // Default color
        
        // Set color based on district type
        switch(districtType) {
            case 'SCHOOL': fillColor = '#E57373'; break;
            case 'CITY': fillColor = '#64B5F6'; break;
            case 'FIRE': fillColor = '#FFB74D'; break;
            case 'COUNTY': fillColor = '#81C784'; break;
            case 'LIBRARY': fillColor = '#9575CD'; break;
            case 'PORT': fillColor = '#4FC3F7'; break;
            case 'HOSPITAL': fillColor = '#F06292'; break;
            case 'CEMETERY': fillColor = '#90A4AE'; break;
        }
        
        // Create the polygon
        const polygon = new google.maps.Polygon({
            paths: district.polygonCoords,
            strokeColor: fillColor,
            strokeOpacity: 0.9,
            strokeWeight: 2,
            fillColor: fillColor,
            fillOpacity: 0.25,
            map: map,
            zIndex: 1
        });
        
        // Add click event to polygon
        polygon.addListener('click', function() {
            // Pan to the center of the district
            map.panTo({ lat: district.latitude, lng: district.longitude });
            
            // Show district info
            showDistrictInfo(district);
        });
        
        // Add hover effects
        polygon.addListener('mouseover', function() {
            this.setOptions({
                fillOpacity: 0.5,
                strokeWeight: 3,
                zIndex: 100
            });
        });
        
        polygon.addListener('mouseout', function() {
            this.setOptions({
                fillOpacity: 0.25,
                strokeWeight: 2,
                zIndex: 1
            });
        });
        
        return polygon;
    }
    
    // Create custom marker for district
    function createDistrictMarker(district) {
        const districtType = district.district_type || 'OTHER';
        
        // Create marker
        const marker = new google.maps.Marker({
            position: { lat: district.latitude, lng: district.longitude },
            map: map,
            title: district.district_name,
            // Custom icon setup using HTML element
            icon: {
                url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(
                    `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40">
                        <circle cx="20" cy="20" r="20" fill="rgba(0,0,0,0)" />
                    </svg>`
                ),
                anchor: new google.maps.Point(20, 20),
                scaledSize: new google.maps.Size(40, 40)
            },
            optimized: false,
            zIndex: 10
        });
        
        // Add custom HTML overlay for marker
        const markerOverlay = new google.maps.OverlayView();
        markerOverlay.draw = function() {
            this.div_ = document.createElement('div');
            this.div_.className = `district-marker marker-${districtType}`;
            this.div_.innerHTML = district.district_code || districtType.charAt(0);
            this.div_.title = district.district_name;
            this.div_.setAttribute('data-district-id', district.id);
            
            const panes = this.getPanes();
            panes.overlayMouseTarget.appendChild(this.div_);
            
            const point = this.getProjection().fromLatLngToDivPixel(marker.getPosition());
            if (point) {
                this.div_.style.left = (point.x - 20) + 'px';
                this.div_.style.top = (point.y - 20) + 'px';
            }
        };
        
        markerOverlay.onRemove = function() {
            if (this.div_) {
                this.div_.parentNode.removeChild(this.div_);
                delete this.div_;
            }
        };
        
        markerOverlay.setMap(map);
        
        // Add click event to marker
        marker.addListener('click', function() {
            showDistrictInfo(district);
        });
        
        return marker;
    }
    
    // Apply filters to the map markers
    function applyFilters() {
        if (currentFilters.length === 0) {
            // Show all markers and polygons if no filters
            markers.forEach(marker => marker.setVisible(true));
            polygons.forEach(polygon => polygon.setVisible(true));
            
            // Show all district cards
            document.querySelectorAll('.district-card').forEach(card => {
                card.style.display = 'block';
            });
            
            return;
        }
        
        // Filter markers and polygons
        districtsData.forEach((district, index) => {
            const isVisible = currentFilters.includes(district.district_type);
            
            // Update marker visibility
            if (index < markers.length) {
                markers[index].setVisible(isVisible);
            }
            
            // Update polygon visibility
            if (index < polygons.length) {
                polygons[index].setVisible(isVisible);
            }
        });
        
        // Filter district cards
        document.querySelectorAll('.district-card').forEach(card => {
            const type = card.getAttribute('data-type');
            card.style.display = currentFilters.includes(type) ? 'block' : 'none';
        });
    }
    
    // Show district info in the panel
    function showDistrictInfo(district) {
        const panel = document.getElementById('districtInfoPanel');
        
        // Update panel content
        document.getElementById('districtName').textContent = district.district_name;
        document.getElementById('districtCode').textContent = district.district_code || 'N/A';
        document.getElementById('districtType').textContent = formatDistrictType(district.district_type);
        document.getElementById('districtLevyRate').textContent = formatNumber(district.levy_rate) + '%';
        document.getElementById('districtLevyAmount').textContent = formatCurrency(district.levy_amount);
        
        // Set active district
        activeDistrictId = district.id;
        
        // Add link to district detail
        const detailLink = document.getElementById('districtDetailLink');
        detailLink.href = `/public/district/${district.id}`;
        
        // Show the panel
        panel.classList.add('visible');
        
        // Highlight selected district card
        document.querySelectorAll('.district-card').forEach(card => {
            const cardId = parseInt(card.getAttribute('data-id'));
            if (cardId === district.id) {
                card.classList.add('border-primary', 'shadow');
                
                // Scroll to the card if in carousel
                const carousel = document.getElementById('districtCarousel');
                if (!carousel.classList.contains('expanded')) {
                    card.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
                }
            } else {
                card.classList.remove('border-primary', 'shadow');
            }
        });
    }
    
    // Close the info panel
    function closeInfoPanel() {
        const panel = document.getElementById('districtInfoPanel');
        panel.classList.remove('visible');
        activeDistrictId = null;
        
        // Remove highlight from all cards
        document.querySelectorAll('.district-card').forEach(card => {
            card.classList.remove('border-primary', 'shadow');
        });
    }
    
    // Format district type for display
    function formatDistrictType(type) {
        if (!type) return 'Unknown';
        
        // Convert SCHOOL to "School District", etc.
        return type.charAt(0) + type.slice(1).toLowerCase().replace('_', ' ');
    }
    
    // Format number with commas
    function formatNumber(num) {
        if (num === null || num === undefined) return '0.00';
        return parseFloat(num).toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,');
    }
    
    // Format currency
    function formatCurrency(num) {
        if (num === null || num === undefined) return '$0.00';
        return '$' + formatNumber(num);
    }
    
    // Populate the district carousel
    function populateDistrictCarousel() {
        const carousel = document.getElementById('districtCarousel');
        carousel.innerHTML = '';
        
        districtsData.forEach(district => {
            const card = document.createElement('div');
            card.className = `district-card district-card-${district.district_type.toLowerCase()}`;
            card.setAttribute('data-id', district.id);
            card.setAttribute('data-type', district.district_type);
            
            card.innerHTML = `
                <div class="card-body p-3">
                    <h5 class="card-title mb-1 fw-bold">${district.district_name}</h5>
                    <p class="text-muted mb-2 small">${district.district_code || 'No Code'} · ${formatDistrictType(district.district_type)}</p>
                    <div class="d-flex justify-content-between">
                        <div>
                            <p class="mb-0 small">Levy Rate</p>
                            <p class="fw-bold mb-0">${formatNumber(district.levy_rate)}%</p>
                        </div>
                        <div class="text-end">
                            <p class="mb-0 small">Levy Amount</p>
                            <p class="fw-bold mb-0">${formatCurrency(district.levy_amount)}</p>
                        </div>
                    </div>
                </div>
            `;
            
            card.addEventListener('click', function() {
                // Get the district id from the card
                const id = parseInt(this.getAttribute('data-id'));
                // Find the district data
                const district = districtsData.find(d => d.id === id);
                
                if (district) {
                    // Pan to the district on the map
                    map.panTo({ lat: district.latitude, lng: district.longitude });
                    map.setZoom(13);
                    
                    // Show district info
                    showDistrictInfo(district);
                }
            });
            
            carousel.appendChild(card);
        });
    }
    
    // Setup UI interactions
    function setupUIInteractions() {
        // Close button for info panel
        document.getElementById('closeInfoPanel').addEventListener('click', closeInfoPanel);
        
        // Toggle for district type filters
        document.querySelectorAll('.filter-badge').forEach(badge => {
            badge.addEventListener('click', function() {
                const type = this.getAttribute('data-type');
                
                if (this.classList.contains('inactive')) {
                    // Add filter
                    this.classList.remove('inactive');
                    currentFilters.push(type);
                } else {
                    // Remove filter
                    this.classList.add('inactive');
                    currentFilters = currentFilters.filter(t => t !== type);
                }
                
                applyFilters();
            });
        });
        
        // Reset filters button
        document.getElementById('resetFilters').addEventListener('click', function() {
            // Reset all filters
            document.querySelectorAll('.filter-badge').forEach(badge => {
                badge.classList.remove('inactive');
            });
            
            currentFilters = [];
            applyFilters();
            
            // Reset map zoom and center
            map.fitBounds(bounds);
        });
        
        // Toggle carousel expanded view
        document.getElementById('carouselToggle').addEventListener('click', function() {
            const carousel = document.getElementById('districtCarousel');
            carousel.classList.toggle('expanded');
            this.classList.toggle('expanded');
            
            if (carousel.classList.contains('expanded')) {
                this.textContent = 'Minimize Cards';
                
                // Close info panel when expanding carousel
                closeInfoPanel();
            } else {
                this.textContent = 'Expand Cards';
            }
        });
        
        // Map control buttons
        document.getElementById('zoomInBtn').addEventListener('click', function() {
            map.setZoom(map.getZoom() + 1);
        });
        
        document.getElementById('zoomOutBtn').addEventListener('click', function() {
            map.setZoom(map.getZoom() - 1);
        });
        
        document.getElementById('resetMapBtn').addEventListener('click', function() {
            map.fitBounds(bounds);
        });
    }
    
    // Initialize map when Google Maps API is loaded
    if (typeof google !== 'undefined') {
        initMap();
    } else {
        console.error('Google Maps API not loaded');
    }
});
