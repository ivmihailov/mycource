from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("accounts/", include("apps.users.urls")),
    path("courses/", include("apps.courses.urls")),
    path("lessons/", include("apps.lessons.urls")),
    path("quizzes/", include("apps.quizzes.urls")),
    path("learning/", include("apps.learning.urls")),
    path("interactions/", include("apps.interactions.urls")),
    path("ai/", include("apps.ai_support.urls")),
    path("api/", include("apps.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = "apps.core.views.custom_page_not_found"
handler500 = "apps.core.views.custom_server_error"
