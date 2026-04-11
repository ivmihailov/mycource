from django.urls import path

from apps.core.views import DashboardView, HomePageView, StaffStatsView

app_name = "core"

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("staff/stats/", StaffStatsView.as_view(), name="staff_stats"),
]
