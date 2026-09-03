from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProduceForm
from .models import Produce
@login_required

def my_produce(request):
    produce_list = Produce.objects.filter(
        farmer=request.user
    ).order_by("-created_at")

    selected_status = request.GET.get("status", "").upper()
    valid_statuses = {
        choice[0] for choice in Produce.STATUS_CHOICES
    }
    if selected_status not in valid_statuses:
        selected_status = ""

    filtered_produce = produce_list
    if selected_status:
        filtered_produce = produce_list.filter(status=selected_status)

    search_query = request.GET.get("search", "").strip()
    if search_query:
        filtered_produce = filtered_produce.filter(
            crop_name__icontains=search_query
        )

    produce_counts = {
        "all": produce_list.count(),
        "available": produce_list.filter(status="AVAILABLE").count(),
        "requested": produce_list.filter(status="REQUESTED").count(),
        "procured": produce_list.filter(status="PROCURED").count(),
    }

    return render(
        request,
        "produce/my_produce.html",
        {
            "produce_list": filtered_produce,
            "produce_counts": produce_counts,
            "selected_status": selected_status,
            "search_query": search_query,
        },
    )

@login_required
def add_produce(request):
    if request.method == "POST":
        form = ProduceForm(request.POST)

        if form.is_valid():
            produce = form.save(commit=False)
            produce.farmer = request.user
            produce.save()

            return render(
                request,
                "produce/redirect_to_my_produce.html",
            )

    else:
        form = ProduceForm()

    return render(
        request,
        "produce/add_produce.html",
        {
            "form": form,
        },
    )


@login_required
def produce_detail(request, pk):
    produce = get_object_or_404(
        Produce,
        pk=pk,
        farmer=request.user,
    )

    return render(
        request,
        "produce/detail.html",
        {"produce": produce},
    )


@login_required
def edit_produce(request, pk):
    produce = get_object_or_404(
        Produce,
        pk=pk,
        farmer=request.user,
    )

    if produce.status != "AVAILABLE":
        return redirect("produce:my_produce")

    if request.method == "POST":
        form = ProduceForm(
            request.POST,
            instance=produce,
        )

        if form.is_valid():
            form.save()

            return render(
                request,
                "produce/redirect_to_my_produce.html",
            )

    else:
        form = ProduceForm(instance=produce)

    return render(
        request,
        "produce/add_produce.html",
        {
            "form": form,
            "editing": True,
            "produce": produce,
        },
    )

@login_required
def delete_produce(request, pk):
    produce = get_object_or_404(
        Produce,
        pk=pk,
        farmer=request.user,
    )

    if produce.status != "AVAILABLE":
        return redirect("produce:my_produce")

    if request.method == "POST":
        produce.delete()

        return render(
            request,
            "produce/redirect_to_my_produce.html",
        )

    return redirect("produce:my_produce")