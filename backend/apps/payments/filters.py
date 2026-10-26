from datetime import date, datetime, time, timedelta

from django.utils import timezone


def filter_invoices(queryset, data):
    if data.get("venue") is not None:
        queryset = queryset.filter(venue_id=data["venue"])
    zone = timezone.get_default_timezone()
    if data.get("start_date"):
        start = timezone.make_aware(datetime.combine(data["start_date"], time.min), zone)
        queryset = queryset.filter(issued_at__gte=start)
    if data.get("end_date") and data["end_date"] < date.max:
        # Avoid SQL date conversion: MySQL timezone tables are optional.
        until = timezone.make_aware(datetime.combine(data["end_date"] + timedelta(days=1), time.min), zone)
        queryset = queryset.filter(issued_at__lt=until)
    if data.get("number"):
        queryset = queryset.filter(number__icontains=data["number"])
    return queryset
