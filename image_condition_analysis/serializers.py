from image_condition_analysis.models import (
    AnalysisTask,
    ImageConditionAnalysis,
    OverallImageAnalysis,
    Prompt,
    Property,
    PropertyImage,
    WorkflowStatus,
)
from rest_framework import serializers


class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = [
            "id",
            "image",
            "original_url",
            "main_category",
            "sub_category",
            "room_type",
            "condition_label",
            "reasoning",
        ]


class ImageConditionAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageConditionAnalysis
        fields = [
            "id",
            "super_id",
            "image_url",
            "image_id",
            "main_category",
            "image_room_name",
            "image_room_type",
            "image_group_number",
            "merged_image_number",
            "merged_image_urls",
            "similarity_image_excellent",
            "similarity_image_above_average",
            "similarity_image_below_average",
            "similarity_image_poor",
            "image_condition_score",
            "image_condition_label",
            "image_condition_explanation",
        ]


class OverallImageAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = OverallImageAnalysis
        fields = [
            "super_id",
            "property_url",
            "total_images_processed",
            "distribution_images_excellent",
            "distribution_images_above_average",
            "distribution_images_below_average",
            "distribution_images_poor",
            "overall_condition_score",
            "overall_condition_label",
            "images_of_concern",
            "number_of_bedrooms",
            "condition_confidence_beds",
            "condition_explanation",
        ]


class PropertySerializer(serializers.ModelSerializer):
    images = PropertyImageSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = [
            "id",
            "url",
            "orch_property_id",
            "super_id",
            "address",
            "price",
            "bedrooms",
            "bathrooms",
            "size",
            "house_type",
            "agent",
            "image_urls",
            "floorplan_urls",
            "failed_downloads",
            "created_at",
            "updated_at",
            "images",
        ]


class AnalysisTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisTask
        fields = [
            "id",
            "super_id",
            "status",
            "progress",
            "stage",
            "stage_progress",
            "notes",
            "created_at",
            "updated_at",
        ]


class PromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prompt
        fields = ["name", "content"]  # , "spaces"]


class PromptUpdateSerializer(serializers.Serializer):
    name = serializers.CharField()
    content = serializers.CharField()
    # spaces = serializers.ListField(child=serializers.CharField(), required=False)


class WorkflowCallbackSerializer(serializers.Serializer):
    url = serializers.URLField()
    headers = serializers.DictField(
        child=serializers.CharField(), required=False, allow_empty=True
    )


class DirectAnalysisRequestSerializer(serializers.Serializer):
    super_id = serializers.CharField()
    property_id = serializers.CharField(required=False, allow_blank=True)
    image_urls = serializers.ListField(child=serializers.URLField(), allow_empty=False)
    notes = serializers.DictField(required=False)
    callback = WorkflowCallbackSerializer(required=False)


class WorkflowStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowStatus
        fields = [
            "super_id",
            "property_id",
            "context",
            "status",
            "stage",
            "progress",
            "data_location",
            "last_error",
            "created_at",
            "updated_at",
        ]


class WorkflowStatusUpdateSerializer(serializers.Serializer):
    context = serializers.CharField(max_length=64)
    status = serializers.CharField(max_length=64)
    property_id = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )
    stage = serializers.CharField(required=False, allow_blank=True, max_length=128)
    progress = serializers.FloatField(required=False)
    data_location = serializers.CharField(required=False, allow_blank=True, max_length=2048)
    last_error = serializers.CharField(required=False, allow_blank=True)
