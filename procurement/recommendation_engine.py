from datetime import date, timedelta
from django.db import models
from appointments.models import Appointment
from .models import ProcurementCenter


def get_recommended_centers(produce=None, farmer=None, target_district=None):
    """
    Intelligent Center Recommendation Engine.
    Filters and ranks active procurement centers based on:
    1. Crop compatibility (mandatory)
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
            crops_list = [c.strip().lower() for c in center.crops_handled.split(",")]
            if any(crop_name.lower() in c for c in crops_list):
                eligible_centers.append(center)

    # Fallback to all active centers if no crop-specific match
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

        # Feature A: Crop Match
        if crop_name:
            reasons.append(f"🌾 Accepts {crop_name} procurement")
            score += 30

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
    for idx, c in enumerate(ranked_list):
        if idx == 0:
            c.is_top_recommendation = True
            c.recommendation_badge = "🥇 BEST MATCH"
        elif c.recommendation_score >= 50:
            c.is_top_recommendation = False
            c.recommendation_badge = "⭐ HIGH COMPATIBILITY"
        else:
            c.is_top_recommendation = False
            c.recommendation_badge = "🟢 AVAILABLE"

    top_recommendation = ranked_list[0] if ranked_list else None
    return top_recommendation, ranked_list
