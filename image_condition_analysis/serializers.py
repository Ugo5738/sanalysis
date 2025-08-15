from image_condition_analysis.models import (
    AnalysisTask,
    ImageConditionAnalysis,
    OverallImageAnalysis,
    Prompt,
    Property,
    PropertyImage,
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


class DirectAnalysisRequestSerializer(serializers.Serializer):
    super_id = serializers.CharField()
    image_urls = serializers.ListField(child=serializers.URLField(), allow_empty=False)
    notes = serializers.DictField(required=False)
