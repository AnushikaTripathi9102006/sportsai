from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from produce.models import Produce


@login_required
def token_queue(request):
    profile = getattr(request.user, "profile", None)

    produce_list = Produce.objects.filter(farmer=request.user).order_by("-created_at")
    active_produce = produce_list.filter(status="REQUESTED").first() or produce_list.first()

    is_your_turn = request.GET.get("turn") == "true"

    token_number = None
    queue_data = None
    if active_produce:
        token_number = f"A-1{active_produce.id:02d}"

        current_token = token_number if is_your_turn else "A-092"
        your_position = 1 if is_your_turn else 12
        farmers_ahead = 0 if is_your_turn else 11
        estimated_wait = "Now" if is_your_turn else "~45 minutes"

        queue_data = {
            "current_token": current_token,
            "your_position": your_position,
            "farmers_ahead": farmers_ahead,
            "estimated_wait": estimated_wait,
            "is_your_turn": is_your_turn,
            "counter_number": "Counter 2",
            "center_name": "Lucknow Procurement Hub",
        }

    return render(
        request,
        "tokens/token_queue.html",
        {
            "farmer": request.user,
            "profile": profile,
            "active_produce": active_produce,
            "token_number": token_number,
            "queue": queue_data,
            "is_your_turn": is_your_turn,
        },
    )
