"""Opt-in personal-area, family-sharing, and nearby-help endpoints."""
import hashlib
import logging
import math
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.services import family_repository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/safety", tags=["Safety and Family Sharing"])
_bearer = HTTPBearer(auto_error=False)
_facility_cache = {}
_FACILITY_CACHE_SECONDS = 900
_OVERPASS_URL = "https://overpass-api.de/api/interpreter"


class CreateGroupRequest(BaseModel):
    group_name: str = Field(min_length=2, max_length=60)
    member_name: str = Field(min_length=1, max_length=40)


class JoinGroupRequest(BaseModel):
    invite_code: str = Field(min_length=12, max_length=80)
    member_name: str = Field(min_length=1, max_length=40)


class LocationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: Optional[float] = Field(default=None, ge=0, le=100000)


class SharingRequest(BaseModel):
    enabled: bool


class FamilyAlertRequest(BaseModel):
    message: str = Field(default="A family member requested help.", min_length=1, max_length=240)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


def _now():
    return datetime.now(timezone.utc)


def _stamp(dt=None):
    return (dt or _now()).isoformat()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _enabled_or_503():
    if not family_repository.enabled():
        raise HTTPException(503, "Family sharing is awaiting a durable database connection. Personal area checks and nearby help remain available.")


def _authorized_member(group_id: str, credentials: HTTPAuthorizationCredentials | None):
    _enabled_or_503()
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Use a family member access token")
    member = family_repository.member_for_token(group_id, _token_hash(credentials.credentials))
    if not member:
        raise HTTPException(404, "Family group or member access was not found")
    return member


def _distance_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(min(1, a)))


@router.get("/capabilities")
async def capabilities():
    active = family_repository.enabled()
    has_database = bool(__import__("os").getenv("FAMILY_DATABASE_URL"))
    return {
        "personal_location": True,
        "nearby_help": True,
        "family_sharing": active,
        "family_storage": "durable_database" if has_database else ("local_development" if active else "not_configured"),
        "family_message": None if active and has_database else
            ("Family sharing works locally, but needs a durable cloud database before it can be enabled on the hosted site." if active else
             "Family sharing is paused until the durable cloud database is connected. Existing dashboard features are unaffected."),
    }


@router.get("/nearby-help")
async def nearby_help(lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180),
                      radius_km: float = Query(10, ge=1, le=25)):
    """Find mapped shelters and facilities; listings are not verified dispatch contacts."""
    cache_key = (round(lat, 2), round(lon, 2), int(radius_km))
    cached = _facility_cache.get(cache_key)
    now = time.time()
    if cached and now - cached[0] < _FACILITY_CACHE_SECONDS:
        return cached[1]
    radius_m = int(radius_km * 1000)
    query = (f'[out:json][timeout:12];(nwr(around:{radius_m},{lat:.6f},{lon:.6f})'
             '[amenity~"^(police|fire_station|hospital|clinic|doctors)$"];'
             f'nwr(around:{radius_m},{lat:.6f},{lon:.6f})'
             '[emergency~"^(shelter|assembly_point|disaster_response)$"];);out center tags;')
    try:
        async with httpx.AsyncClient(timeout=16, headers={"User-Agent": "DisasterMappingSafetyDashboard/1.0 (public facility lookup)"}) as client:
            response = await client.post(_OVERPASS_URL, data={"data": query})
            response.raise_for_status()
            elements = response.json().get("elements", [])
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Nearby public facility lookup unavailable: %s", exc)
        raise HTTPException(502, "Nearby public facility listings are temporarily unavailable") from exc
    facilities = []
    default_names = {"police": "Police station", "fire_station": "Fire station", "shelter": "Emergency shelter",
                     "hospital": "Hospital", "clinic": "Clinic", "doctors": "Medical practice"}
    for element in elements:
        tags = element.get("tags") or {}
        center = element.get("center") or element
        item_lat, item_lon = center.get("lat"), center.get("lon")
        if item_lat is None or item_lon is None:
            continue
        amenity, emergency = tags.get("amenity", ""), tags.get("emergency", "")
        category = "shelter" if emergency in {"shelter", "assembly_point", "disaster_response"} else amenity
        if category not in default_names:
            continue
        distance = _distance_km(lat, lon, float(item_lat), float(item_lon))
        facilities.append({
            "id": f"{element.get('type')}:{element.get('id')}",
            "name": tags.get("name") or default_names[category], "category": category,
            "latitude": float(item_lat), "longitude": float(item_lon), "distance_km": round(distance, 1),
            "phone": tags.get("phone") or tags.get("contact:phone"), "source": "OpenStreetMap",
        })
    facilities.sort(key=lambda item: item["distance_km"])
    result = {
        "status": "success", "count": len(facilities[:30]), "facilities": facilities[:30],
        "radius_km": radius_km, "source": "OpenStreetMap contributors",
        "notice": "Community-mapped listings can be incomplete or out of date. This system does not contact facilities or dispatch responders. In India, call 112 for emergency response.",
        "emergency_number": "112", "emergency_call_url": "tel:112", "timestamp": _stamp(),
    }
    _facility_cache[cache_key] = (now, result)
    return result


@router.post("/groups")
async def create_group(request: CreateGroupRequest):
    _enabled_or_503()
    group_id, member_id = secrets.token_urlsafe(16), secrets.token_urlsafe(12)
    token, invite_code = secrets.token_urlsafe(32), secrets.token_urlsafe(18)
    try:
        family_repository.create_group(group_id, request.group_name.strip(), _token_hash(invite_code),
                                       member_id, request.member_name.strip(), _token_hash(token), _stamp())
    except Exception as exc:
        logger.exception("Could not create family safety group")
        raise HTTPException(503, "Family storage is unavailable") from exc
    return {"status": "success", "group_id": group_id, "group_name": request.group_name.strip(),
            "member_id": member_id, "member_token": token, "invite_code": invite_code,
            "message": "Keep the invite code private and share it only with trusted family members."}


@router.post("/groups/join")
async def join_group(request: JoinGroupRequest):
    _enabled_or_503()
    member_id, token = secrets.token_urlsafe(12), secrets.token_urlsafe(32)
    try:
        group = family_repository.join_group(_token_hash(request.invite_code.strip()), member_id,
                                             request.member_name.strip(), _token_hash(token), _stamp())
    except Exception as exc:
        logger.exception("Could not join family safety group")
        raise HTTPException(503, "Family storage is unavailable") from exc
    if not group:
        raise HTTPException(404, "Invite code was not found")
    if group.get("error"):
        raise HTTPException(409, group["error"])
    return {"status": "success", "group_id": group["group_id"], "group_name": group["group_name"],
            "member_id": member_id, "member_token": token,
            "message": "You joined the group. Turn on sharing only if you want members to see your location."}


@router.get("/groups/{group_id}")
async def get_group(group_id: str, credentials: HTTPAuthorizationCredentials | None = Security(_bearer)):
    _authorized_member(group_id, credentials)
    group, members, alerts = family_repository.group_details(group_id)
    if not group:
        raise HTTPException(404, "Family group was not found")
    return {"status": "success", "group": group, "members": members, "alerts": alerts,
            "location_retention_days": 30,
            "sharing_note": "Locations update only while sharing is enabled and the member's page remains open. A displayed position is the last location received, with its timestamp."}


@router.patch("/groups/{group_id}/members/{member_id}/sharing")
async def change_sharing(group_id: str, member_id: str, request: SharingRequest,
                         credentials: HTTPAuthorizationCredentials | None = Security(_bearer)):
    member = _authorized_member(group_id, credentials)
    if member["member_id"] != member_id:
        raise HTTPException(403, "Members can only change their own location-sharing setting")
    family_repository.set_sharing(group_id, member_id, request.enabled)
    return {"status": "success", "sharing_enabled": request.enabled,
            "message": "Sharing enabled. Updates require location permission and an open page." if request.enabled else
            "Sharing stopped. Group members can still see the last location and its timestamp."}


@router.put("/groups/{group_id}/members/{member_id}/location")
async def update_location(group_id: str, member_id: str, request: LocationRequest,
                          credentials: HTTPAuthorizationCredentials | None = Security(_bearer)):
    member = _authorized_member(group_id, credentials)
    if member["member_id"] != member_id:
        raise HTTPException(403, "Members can only share their own location")
    stamp = _stamp()
    if not family_repository.save_location(group_id, member_id, request.latitude, request.longitude,
                                           request.accuracy_m, stamp):
        raise HTTPException(409, "Turn on location sharing before sending a location")
    # Alerts are generated only when the user's shared point intersects an explicitly
    # assessed HIGH/CRITICAL risk zone. Ordinary weather is not treated as an evacuation warning.
    try:
        from app.services import repository
        zones = repository.list_risk_zones(500)
        for zone in zones:
            level, location = str(zone.get("risk_level", "")).upper(), zone.get("location") or {}
            zlat, zlon = location.get("lat"), location.get("lon")
            if level not in {"HIGH", "CRITICAL"} or zlat is None or zlon is None:
                continue
            distance = _distance_km(request.latitude, request.longitude, float(zlat), float(zlon))
            if distance > 2:
                continue
            zone_id = str(zone.get("zone_id", "unknown"))
            if family_repository.recent_auto_alert(group_id, member_id, zone_id, _stamp(_now() - timedelta(minutes=30))):
                continue
            family_repository.add_alert({
                "alert_id": secrets.token_urlsafe(12), "group_id": group_id, "member_id": member_id,
                "alert_type": "RISK_ZONE", "risk_level": level,
                "message": f"{member['member_name']} shared a location within 2 km of an assessed {level.lower()} risk zone.",
                "latitude": request.latitude, "longitude": request.longitude,
                "metadata": {"zone_id": zone_id, "distance_km": round(distance, 1), "source": "project assessed risk zone"},
                "created_at": stamp,
            })
    except Exception:
        logger.exception("Could not check shared location against assessed risk zones")
    return {"status": "success", "location_updated_at": stamp}


@router.post("/groups/{group_id}/alerts")
async def create_family_alert(group_id: str, request: FamilyAlertRequest,
                              credentials: HTTPAuthorizationCredentials | None = Security(_bearer)):
    member = _authorized_member(group_id, credentials)
    group, _, _ = family_repository.group_details(group_id)
    if not group:
        raise HTTPException(404, "Family group was not found")
    alert = {
        "alert_id": secrets.token_urlsafe(12), "group_id": group_id, "member_id": member["member_id"],
        "alert_type": "HELP", "risk_level": "HIGH", "message": f"{member['member_name']}: {request.message.strip()}",
        "latitude": request.latitude, "longitude": request.longitude,
        "metadata": {"dispatch_status": "not_sent", "note": "This in-app alert does not contact emergency services."},
        "created_at": _stamp(),
    }
    family_repository.add_alert(alert)
    return {"status": "success", "alert_id": alert["alert_id"],
            "message": "Visible to family members in this group. It was not sent to emergency services."}


@router.delete("/groups/{group_id}/members/{member_id}")
async def leave_group(group_id: str, member_id: str,
                      credentials: HTTPAuthorizationCredentials | None = Security(_bearer)):
    member = _authorized_member(group_id, credentials)
    if member["member_id"] != member_id:
        raise HTTPException(403, "Members can only remove their own access")
    family_repository.leave_group(group_id, member_id)
    return {"status": "success", "message": "Your access and saved locations were removed from this group."}
