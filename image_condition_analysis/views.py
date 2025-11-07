from analysis_service.config.logging_config import configure_logger
from image_condition_analysis.models import (
    AnalysisTask,
    ImageConditionAnalysis,
    OverallImageAnalysis,
    Prompt,
    Property,
    WorkflowStatus,
)
from image_condition_analysis.serializers import (
    AnalysisTaskSerializer,
    DirectAnalysisRequestSerializer,
    ImageConditionAnalysisSerializer,
    OverallImageAnalysisSerializer,
    PromptUpdateSerializer,
    WorkflowStatusSerializer,
    WorkflowStatusUpdateSerializer,
)
from image_condition_analysis.tasks import analyze_images_direct
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# image_condition_analysis.messaging import send_whatsapp_message

logger = configure_logger(__name__)


class ImageConditionAnalysisViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ImageConditionAnalysis.objects.all()
    serializer_class = ImageConditionAnalysisSerializer

    def get_queryset(self):
        qs = super().get_queryset().order_by("super_id", "image_id")
        super_id = self.request.query_params.get("super_id")
        if super_id:
            qs = qs.filter(super_id=super_id)
        return qs


class OverallImageAnalysisViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OverallImageAnalysis.objects.all()
    serializer_class = OverallImageAnalysisSerializer

    def get_queryset(self):
        qs = super().get_queryset().order_by("super_id")
        super_id = self.request.query_params.get("super_id")
        if super_id:
            qs = qs.filter(super_id=super_id)
        return qs


class AnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DirectAnalysisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        super_id = data["super_id"]
        image_urls = data["image_urls"]
        property_id = data.get("property_id") or None
        notes = data.get("notes")
        callback = data.get("callback")

        if Property.objects.filter(super_id=super_id).exists():
            logger.warning(
                "Rejecting analyze request: Property with super_id=%s already exists",
                super_id,
            )
            return Response(
                {
                    "detail": (
                        "A workflow already exists for super_id=%s. "
                        "Please request a new super_id before retrying." % super_id
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        analyze_images_direct.delay(
            super_id, image_urls, notes, callback, property_id=property_id
        )

        return Response(
            {"super_id": super_id, "images": len(image_urls), "status": "queued"},
            status=status.HTTP_202_ACCEPTED,
        )


class PromptUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PromptUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        name = data["name"]
        content = data["content"]
        # spaces = data.get("spaces", [])

        # Get the current active prompt to find current version
        current_prompt = (
            Prompt.objects.filter(name=name, is_active=True)
            .order_by("-version")
            .first()
        )
        if current_prompt:
            new_version = current_prompt.version + 1
            # Deactivate old version
            current_prompt.is_active = False
            current_prompt.save()
        else:
            new_version = 1

        # Create the new version
        new_prompt = Prompt.objects.create(
            name=name,
            content=content,
            # spaces=spaces,
            version=new_version,
            is_active=True,
        )

        return Response(
            {"message": f"Prompt {name} updated to version {new_version}."},
            status=status.HTTP_200_OK,
        )


class GetPromptView(APIView):
    def get(self, request):
        name = request.query_params.get("name")

        if not name:
            return Response(
                {"error": "Missing 'name' query parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch the active/latest version of the prompt
        prompt = (
            Prompt.objects.filter(name=name, is_active=True)
            .order_by("-version")
            .first()
        )
        if not prompt:
            return Response(
                {"error": f"No active prompt found for name: {name}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = {
            "name": prompt.name,
            "content": prompt.content,
            "version": prompt.version,
            "is_active": prompt.is_active,
        }
        return Response(data, status=status.HTTP_200_OK)


class WorkflowStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, super_id, context=None):
        queryset = WorkflowStatus.objects.filter(super_id=super_id)
        if context:
            record = queryset.filter(context=context).first()
            if not record:
                return Response(
                    {
                        "detail": f"No workflow status found for super_id={super_id} context={context}"
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            serializer = WorkflowStatusSerializer(record)
            return Response(serializer.data)

        serializer = WorkflowStatusSerializer(queryset, many=True)
        return Response(serializer.data)

    def put(self, request, super_id, context=None):
        incoming = request.data.copy()
        if context and "context" not in incoming:
            incoming["context"] = context

        serializer = WorkflowStatusUpdateSerializer(data=incoming)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        context_value = payload["context"]

        record, created = WorkflowStatus.objects.get_or_create(
            super_id=super_id,
            context=context_value,
            defaults={
                "property_id": payload.get("property_id"),
                "status": payload["status"],
                "stage": payload.get("stage"),
                "progress": payload.get("progress"),
                "data_location": payload.get("data_location"),
                "last_error": payload.get("last_error"),
            },
        )
        if not created:
            record.status = payload["status"]
            for field in ["property_id", "stage", "progress", "data_location", "last_error"]:
                if field in payload:
                    setattr(record, field, payload.get(field))
        record.save()

        output = WorkflowStatusSerializer(record)
        return Response(output.data, status=status.HTTP_200_OK)
