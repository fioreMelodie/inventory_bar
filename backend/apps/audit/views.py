from datetime import date, datetime, time, timedelta

from django.utils import timezone
from rest_framework import generics

from apps.accounts.permissions import IsAdministrator
from .models import AuditEvent, EventType
from .serializers import AuditEventDetailSerializer, AuditEventSerializer, AuditFilterSerializer


class AuditEventListView(generics.ListAPIView):
    permission_classes = [IsAdministrator]
    serializer_class = AuditEventSerializer

    def get_queryset(self):
        filters = AuditFilterSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        data = filters.validated_data
        queryset = AuditEvent.objects.order_by("-created_at", "-pk")
        zone = timezone.get_default_timezone()
        if data.get("start_date"):
            start = timezone.make_aware(datetime.combine(data["start_date"], time.min), zone)
            queryset = queryset.filter(created_at__gte=start)
        if data.get("end_date") and data["end_date"] < date.max:
            until = timezone.make_aware(datetime.combine(data["end_date"] + timedelta(days=1), time.min), zone)
            queryset = queryset.filter(created_at__lt=until)
        if data.get("username"):
            queryset = queryset.filter(username__icontains=data["username"])
        if data.get("event_type"):
            queryset = queryset.filter(event_type=data["event_type"])
        venue = data.get("venue")
        if venue == "__unrecorded__":
            queryset = queryset.filter(venue_recorded=False)
        elif venue == "__none__":
            queryset = queryset.filter(venue_recorded=True, venue__isnull=True)
        elif venue is not None:
            queryset = queryset.filter(venue_id=venue, venue_recorded=True)
        return queryset.defer("description", "ip_address")

    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        response.data["event_types"] = [{"value": value, "label": label} for value, label in EventType.choices]
        response["Cache-Control"] = "no-store"
        return response


class AuditEventDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAdministrator]
    serializer_class = AuditEventDetailSerializer
    queryset = AuditEvent.objects.all()

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response
