import re
from datetime import date, timedelta
from django.db import models
from appointments.models import Appointment
from .models import ProcurementCenter


def is_crop_handled(crop_name, crops_handled_str):
    """
    Checks if a procurement center handles the given crop name.
    Supports names like 'Paddy (Rice)', 'Paddy', 'Rice', 'Wheat (Rabi)', etc.
    """
    if not crop_name or not crops_handled_str:
        return True

    crops_list = [c.strip().lower() for c in crops_handled_str.split(",") if c.strip()]
    crop_lower = crop_name.lower().strip()

    # 1. Direct or bidirectional substring match
    for c in crops_list:
        if c in crop_lower or crop_lower in c:
            return True

    # 2. Word-based overlap match (e.g. "Paddy (Rice)" vs "Paddy")
    crop_words = set(re.findall(r'\w+', crop_lower))
    for c in crops_list:
        c_words = set(re.findall(r'\w+', c))
        if crop_words & c_words:
            return True

    return False


def get_recommended_centers(produce=None, farmer=None, target_district=None):
    """
    Intelligent Center Recommendation Engine.
    Filters and ranks active procurement centers based on:
    1. Crop compatibility (mandatory filter)
    2. Geographic proximity / district match
    3. Live Queue traffic status
    4. Real 7-day appointment slot capacity
    Returns (top_recommendation, ranked_centers_list).
    """
    crop_name = getattr(produce, "crop_name", "").strip() if produce else ""
    district = target_district or getattr(produce, "district", None)
    if not district and farmer and hasattr(farmer, "profile"):
        district = getattr(farmer.profile, "district", None)
    if not district:
        district = "Lucknow"

    # 1. Fetch active centers
    active_centers = ProcurementCenter.objects.filter(is_active=True)

    if not active_centers.exists():
        return None, []

    # 2. Filter crop handling
    eligible_centers = []
    if crop_name:
        for center in active_centers:
            if is_crop_handled(crop_name, center.crops_handled):
                eligible_centers.append(center)

    # Fallback to all active centers ONLY if no center in the entire system handles that crop
    if not eligible_centers:
        eligible_centers = list(active_centers)

    today = date.today()
    next_7_dates = [today + timedelta(days=i) for i in range(1, 8)]
    time_slots = [c[0] for c in Appointment.TIME_SLOT_CHOICES]
    total_max_slots = len(next_7_dates) * len(time_slots) * Appointment.SLOT_CAPACITY

    ranked_list = []

    for center in eligible_centers:
        score = 0.0
        reasons = []

        handles_this_crop = is_crop_handled(crop_name, center.crops_handled) if crop_name else True

        # Feature A: Crop Match
        if crop_name:
            if handles_this_crop:
                reasons.append(f"🌾 Accepts {crop_name} procurement")
                score += 30
            else:
                reasons.append(f"⚠️ Does not handle {crop_name}")
                score -= 200  # Penalize centers that don't handle the crop so they cannot be top recommendation

        # Feature B: District Match & Proximity
        if center.district.lower() == district.lower():
            score += 40
            reasons.append(f"📍 Nearby in your district ({center.district})")
        else:
            reasons.append(f"📍 Located in {center.district} district")

        dist_val = float(center.distance_km or 5.0)
        score -= dist_val * 1.2
        reasons.append(f"⚡ ~{dist_val:.1f} km away")

        # Feature C: Queue Status
        q_status = (center.queue_status or "LOW").upper()
        if q_status == "LOW":
            score += 25
            reasons.append("🟢 Low Queue Traffic")
        elif q_status == "MEDIUM":
            score += 10
            reasons.append("🟡 Medium Queue Traffic")
        else:
            reasons.append("🔴 High Queue Traffic")

        # Feature D: 7-Day Appointment Slot Capacity Calculation
        booked_count = Appointment.objects.filter(
            procurement_center=center,
            appointment_date__in=next_7_dates,
            status="CONFIRMED",
        ).count()

        open_slots = max(0, total_max_slots - booked_count)
        center.open_slots_count = open_slots

        if open_slots > 15:
            score += 30
            reasons.append(f"📅 High Appointment Availability ({open_slots} slots open)")
        elif open_slots > 0:
            score += 15
            reasons.append(f"📅 Slots Available ({open_slots} slots open)")
        else:
            score -= 50
            reasons.append("🔴 Appointment slots full over next 7 days")

        center.recommendation_score = round(score, 1)
        center.reasons = reasons
        ranked_list.append(center)

    # Sort descending by recommendation_score
    ranked_list.sort(key=lambda c: c.recommendation_score, reverse=True)

    # Decorate badges
    top_found = False
    for c in ranked_list:
        handles_this_crop = is_crop_handled(crop_name, c.crops_handled) if crop_name else True
        if not top_found and handles_this_crop:
            c.is_top_recommendation = True
            c.recommendation_badge = "🥇 BEST MATCH"
            top_found = True
        elif c.recommendation_score >= 50 and handles_this_crop:
            c.is_top_recommendation = False
            c.recommendation_badge = "⭐ HIGH COMPATIBILITY"
        else:
            c.is_top_recommendation = False
            c.recommendation_badge = "🟢 AVAILABLE" if handles_this_crop else "⚠️ NO CROP MATCH"

    top_recommendation = next((c for c in ranked_list if (not crop_name or is_crop_handled(crop_name, c.crops_handled))), None)
    return top_recommendation, ranked_list

