"""
IATA airport coordinates lookup + great-circle distance calculation.
Uses a subset of major airports. For production, this would use a full IATA database.
"""
from math import radians, cos, sin, asin, sqrt

# Major airport coordinates (IATA code → (lat, lon))
AIRPORTS = {
    'ATL': (33.6407, -84.4277), 'LAX': (33.9425, -118.4081),
    'ORD': (41.9742, -87.9073), 'DFW': (32.8998, -97.0403),
    'DEN': (39.8561, -104.6737), 'JFK': (40.6413, -73.7781),
    'SFO': (37.6213, -122.3790), 'SEA': (47.4502, -122.3088),
    'LAS': (36.0840, -115.1537), 'MCO': (28.4312, -81.3081),
    'EWR': (40.6895, -74.1745), 'MIA': (25.7959, -80.2870),
    'CLT': (35.2144, -80.9473), 'PHX': (33.4373, -112.0078),
    'IAH': (29.9902, -95.3368), 'BOS': (42.3656, -71.0096),
    'MSP': (44.8848, -93.2223), 'FLL': (26.0742, -80.1506),
    'DTW': (42.2162, -83.3554), 'PHL': (39.8744, -75.2424),
    # International
    'LHR': (51.4700, -0.4543), 'CDG': (49.0097, 2.5479),
    'FRA': (50.0379, 8.5622), 'AMS': (52.3105, 4.7683),
    'DXB': (25.2532, 55.3657), 'SIN': (1.3644, 103.9915),
    'HKG': (22.3080, 113.9185), 'NRT': (35.7720, 140.3929),
    'ICN': (37.4602, 126.4407), 'SYD': (-33.9461, 151.1772),
    'DEL': (28.5562, 77.1000), 'BOM': (19.0896, 72.8656),
    'BLR': (13.1986, 77.7066), 'HYD': (17.2403, 78.4294),
    'MAA': (12.9941, 80.1709), 'CCU': (22.6547, 88.4467),
    'PEK': (40.0799, 116.6031), 'PVG': (31.1443, 121.8083),
    'GRU': (-23.4356, -46.4731), 'MEX': (19.4363, -99.0721),
    'YYZ': (43.6777, -79.6248), 'YVR': (49.1967, -123.1815),
    'MUC': (48.3537, 11.7750), 'FCO': (41.8003, 12.2389),
    'MAD': (40.4983, -3.5676), 'BCN': (41.2971, 2.0785),
    'IST': (41.2753, 28.7519), 'DOH': (25.2609, 51.6138),
}


def haversine_km(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance between two points in km."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # Earth radius in km
    return round(c * r, 2)


def get_distance_km(origin_iata, dest_iata):
    """
    Calculate great-circle distance between two airports.
    Returns (distance_km, success, error_msg).
    """
    origin = origin_iata.strip().upper()
    dest = dest_iata.strip().upper()

    if origin not in AIRPORTS:
        return (None, False, f"Unknown airport code: {origin}")
    if dest not in AIRPORTS:
        return (None, False, f"Unknown airport code: {dest}")

    lat1, lon1 = AIRPORTS[origin]
    lat2, lon2 = AIRPORTS[dest]
    dist = haversine_km(lat1, lon1, lat2, lon2)
    return (dist, True, '')
