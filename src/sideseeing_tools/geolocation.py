from math import asin, cos, radians, sin, sqrt

import requests
import reverse_geocode

COMPONENT_MAPPING = {
    'route': 'street',
    'administrative_area_level_2': 'city',
    'administrative_area_level_1': 'state',
    'country': 'country',
}
EARTH_RADIUS_KM = 6371


def inverse_geocode(latitude, longitude, key=None):
    data = {'country': 'Unknown', 'state': 'Unknown', 'city': 'Unknown', 'street': 'Unknown'}

    if not key:
        geo = reverse_geocode.search([[latitude, longitude]])

        if geo:
            first_geo = geo.pop()
            data['country'] = first_geo.get('country', 'Unknown')
            data['city'] = first_geo.get('city', 'Unknown')
    else:
        data = inverse_geocode_from_google(latitude, longitude, key)

    return data


def inverse_geocode_from_google(latitude, longitude, key):
    """Performs reverse geocoding using Google's Geocoding API to find address components."""

    data = {v: 'Unknown' for v in COMPONENT_MAPPING.values()}

    try:
        params = {'latlng': f'{float(latitude)},{float(longitude)}', 'key': key}
        response = requests.get('https://maps.googleapis.com/maps/api/geocode/json', params=params)
        response.raise_for_status()
        results = response.json().get("results", [])

        if not results:
            return data

        for component in results[0].get('address_components', []):
            for component_type, data_key in COMPONENT_MAPPING.items():
                if component_type in component.get('types', []):
                    data[data_key] = component.get('long_name')
    except requests.exceptions.RequestException as e:
        print(f"ERROR. Failed to call Google Geocoding API: {e}")

    return data


def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the latitude/longitude distance between two points in km."""

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))

    return EARTH_RADIUS_KM * c
