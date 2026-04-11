from django.urls import path

from apps.interactions.views import add_comment, delete_comment, toggle_favorite, upsert_review

app_name = "interactions"

urlpatterns = [
    path("courses/<slug:slug>/favorite/", toggle_favorite, name="toggle_favorite"),
    path("courses/<slug:slug>/comments/", add_comment, name="add_comment"),
    path("comments/<int:pk>/delete/", delete_comment, name="delete_comment"),
    path("courses/<slug:slug>/review/", upsert_review, name="upsert_review"),
]
