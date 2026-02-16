from django.urls import path
from .views import (
    index,
    rollover_create,
    rollover_detail,
    rollover_delete,
    api_recommendations,
    api_round_update,
    api_rollover_progress,
)

urlpatterns = [
    path("", index, name="index"),
    path("rollovers/create/", rollover_create, name="rollover_create"),
    path("rollovers/<int:rollover_id>/", rollover_detail, name="rollover_detail"),
    path(
        "rollovers/<int:rollover_id>/delete/", rollover_delete, name="rollover_delete"
    ),
    path("api/recommendations/", api_recommendations, name="api_recommendations"),
    path(
        "api/rounds/<int:round_id>/update/", api_round_update, name="api_round_update"
    ),
    path(
        "api/rollovers/<int:rollover_id>/progress/",
        api_rollover_progress,
        name="api_rollover_progress",
    ),
]
