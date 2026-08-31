from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProduceForm
from .models import Produce
@login_required

def my_produce(request):
    produce_list = Produce.objects.filter(
        farmer=request.user
    ).order_by("-created_at")

    return render(
        request,
        "produce/my_produce.html",
        {"produce_list": produce_list},
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