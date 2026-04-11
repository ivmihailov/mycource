from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.ai_support.services import get_ai_advisor


@login_required
@require_POST
def advice_panel(request):
    context_type = request.POST.get("context_type", "student_hint")
    advisor = get_ai_advisor()
    advice = advisor.get_advice(context_type=context_type, payload=request.POST.dict())
    return render(
        request,
        "ai_support/partials/advice_panel.html",
        {"advice": advice, "context_type": context_type},
    )
