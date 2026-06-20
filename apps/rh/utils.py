"""
apps/rh/utils.py
Utilitaires géographiques pour le pointage de présence.
"""

import math


def haversine_m(lat1, lon1, lat2, lon2):
    """
    Distance en mètres entre deux points GPS (formule de Haversine).
    Les arguments peuvent être des float, Decimal ou str numériques.
    """
    lat1, lon1, lat2, lon2 = (float(lat1), float(lon1), float(lat2), float(lon2))
    rayon_terre = 6371000.0  # mètres
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * rayon_terre * math.asin(math.sqrt(a))


def point_reference_employe(employe):
    """
    Retourne le point de référence (lat, lon, type) contre lequel comparer le
    pointage d'un employé : son dépôt s'il a des coordonnées, sinon le point
    central de sa zone, sinon (None, None, 'aucune').
    """
    depot = getattr(employe, 'depot', None)
    if depot and depot.latitude is not None and depot.longitude is not None:
        return depot.latitude, depot.longitude, 'depot'
    zone = getattr(depot, 'zone', None) if depot else None
    if zone and zone.latitude is not None and zone.longitude is not None:
        return zone.latitude, zone.longitude, 'zone'
    return None, None, 'aucune'
