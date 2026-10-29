from django.urls import path

from .views import AuditEventDetailView, AuditEventListView

app_name = "audit"
urlpatterns = [
    path("audit/events/", AuditEventListView.as_view(), name="event-list"),
    path("audit/events/<int:pk>/", AuditEventDetailView.as_view(), name="event-detail"),
]
