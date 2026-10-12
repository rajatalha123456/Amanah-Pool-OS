"""Public website enquiries: a throttled public submission endpoint and a Super Admin inbox."""

from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.permissions import HasAnyRole

from .models import DemoRequest


class DemoRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemoRequest
        fields = ("id", "name", "organisation", "email", "interest", "message", "handled", "created_at")
        read_only_fields = ("id", "handled", "created_at")


class DemoRequestInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    organisation = serializers.CharField(max_length=160)
    email = serializers.EmailField()
    interest = serializers.ChoiceField(choices=[c for c, _ in DemoRequest.INTERESTS], default="other")
    message = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")
    website = serializers.CharField(required=False, allow_blank=True, default="")  # honeypot: humans leave it empty


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([ScopedRateThrottle])
def submit_demo_request(request):
    """Public: a visitor asks for a demo. Throttled per address; a filled honeypot is dropped silently."""
    serializer = DemoRequestInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    if data["website"]:
        return Response({"received": True}, status=201)  # a bot: pretend success, store nothing
    DemoRequest.objects.create(
        name=data["name"].strip(), organisation=data["organisation"].strip(), email=data["email"].lower(),
        interest=data["interest"], message=data["message"].strip(),
    )
    return Response({"received": True}, status=201)


submit_demo_request.cls.throttle_scope = "public_form"


class DemoRequestViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Platform Super Admin only: the enquiries received from the website."""

    serializer_class = DemoRequestSerializer
    permission_classes = [IsAuthenticated, HasAnyRole(["platform_super_admin"])]

    def get_queryset(self):
        return DemoRequest.objects.all()

    @action(detail=True, methods=["post"], url_path="mark-handled")
    def mark_handled(self, request, pk=None):
        item = self.get_object()
        item.handled = True
        item.save(update_fields=["handled", "updated_at"])
        return Response(self.get_serializer(item).data)
