from rest_framework import serializers

from .models import AuditEvent, EventType


class AuditFilterSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False, input_formats=["%Y-%m-%d"])
    end_date = serializers.DateField(required=False, input_formats=["%Y-%m-%d"])
    username = serializers.CharField(max_length=150, required=False)
    event_type = serializers.ChoiceField(choices=EventType.choices, required=False)
    venue = serializers.CharField(max_length=32, required=False)

    def validate_venue(self, value):
        if value in ("__unrecorded__", "__none__"):
            return value
        try:
            venue = int(value)
        except ValueError:
            raise serializers.ValidationError("Select a valid venue.")
        if not 0 < venue <= 9223372036854775807:
            raise serializers.ValidationError("Select a valid venue.")
        return venue

    def validate(self, attrs):
        start, end = attrs.get("start_date"), attrs.get("end_date")
        if start and end and start > end:
            raise serializers.ValidationError({"end_date": "End date must be on or after start date."})
        return attrs


class AuditEventSerializer(serializers.ModelSerializer):
    event_type_label = serializers.CharField(source="get_event_type_display", read_only=True)

    class Meta:
        model = AuditEvent
        fields = ("id", "username", "event_type", "event_type_label", "entity", "entity_id",
                  "venue", "venue_name", "venue_recorded", "created_at")
        read_only_fields = fields


class AuditEventDetailSerializer(AuditEventSerializer):
    class Meta(AuditEventSerializer.Meta):
        fields = AuditEventSerializer.Meta.fields + ("description", "ip_address")
        read_only_fields = fields
