import hashlib

from django.db import models
from django.utils.translation import gettext_lazy as _
from helpers.models import TrackingModel


class Prompt(TrackingModel):
    name = models.CharField(max_length=100)
    content = models.TextField()
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "prompt"
        ordering = ["-updated_at", "-version"]

    def __str__(self):
        return f"{self.name} (v{self.version})"


class Property(TrackingModel):
    super_id = models.CharField(
        max_length=1028, null=True, blank=True, verbose_name=("Super ID")
    )
    bedrooms = models.IntegerField(null=True, blank=True)
    bathrooms = models.IntegerField(null=True, blank=True)
    floorplan_urls = models.JSONField(default=list, blank=True)
    failed_downloads = models.JSONField(default=list)
    image_urls = models.JSONField(default=list)

    class Meta:
        db_table = "property"
        verbose_name = _("Property")
        verbose_name_plural = _("Properties")

    def __str__(self):
        return f"Property: {self.super_id}"


class PropertyImage(TrackingModel):
    property = models.ForeignKey(
        Property, related_name="images", on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to="property_images/")
    original_url = models.URLField()
    main_category = models.CharField(
        max_length=100
    )  # e.g., "internal", "external", "floor plan"
    sub_category = models.CharField(
        max_length=100
    )  # e.g., "living_spaces", "kitchen", "bedroom"
    room_type = models.CharField(
        max_length=100, blank=True
    )  # e.g., "living room", "master bedroom"
    condition_label = models.CharField(max_length=100, blank=True)
    condition_score = models.IntegerField(null=True, blank=True)
    reasoning = models.TextField(blank=True)
    embedding = models.JSONField(null=True, editable=False)
    similarity_scores = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "property_image"
        verbose_name = _("Property Image")
        verbose_name_plural = _("Property Images")


class GroupedImages(TrackingModel):
    property = models.ForeignKey(
        Property, related_name="grouped_images", on_delete=models.CASCADE
    )
    main_category = models.CharField(max_length=100)
    sub_category = models.CharField(max_length=100)
    images = models.ManyToManyField(PropertyImage)

    class Meta:
        db_table = "grouped_images"
        verbose_name = _("Grouped Images")
        verbose_name_plural = _("Grouped Images")
        unique_together = (
            "property",
            "main_category",
            "sub_category",
        )


class MergedPropertyImage(TrackingModel):
    property = models.ForeignKey(
        Property, related_name="merged_images", on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to="merged_property_images/")
    main_category = models.CharField(max_length=100)  # e.g., "internal_living_spaces"
    sub_category = models.CharField(max_length=100)
    images = models.ManyToManyField(PropertyImage)

    class Meta:
        db_table = "merged_property_image"
        verbose_name = _("Merged Property Image")
        verbose_name_plural = _("Merged Property Images")
        # unique_together = ('property', 'main_category', 'sub_category')# TODO: this might need to be changed


class SampleImage(TrackingModel):
    category = models.CharField(max_length=100)  # e.g., "internal"
    subcategory = models.CharField(max_length=100)  # e.g., "living_spaces"
    condition = models.CharField(max_length=100)  # e.g., "excellent"
    image = models.ImageField(upload_to="sample_images/")
    image_hash = models.CharField(max_length=32, unique=True, editable=False)
    embedding = models.JSONField(null=True, editable=False)

    class Meta:
        db_table = "sample_image"
        verbose_name = _("Sample Image")
        verbose_name_plural = _("Sample Images")
        # unique_together = ('category', 'subcategory', 'condition')

    def save(self, *args, **kwargs):
        if not self.image_hash:
            self.image_hash = self.compute_image_hash()
        super().save(*args, **kwargs)

    def compute_image_hash(self):
        """Compute the MD5 hash of the image file."""
        hasher = hashlib.md5()
        if self.image and hasattr(self.image, "path"):
            with open(self.image.path, "rb") as img_file:
                # Read the image in chunks to handle large files efficiently
                for chunk in iter(lambda: img_file.read(4096), b""):
                    hasher.update(chunk)
        return hasher.hexdigest()

    def __str__(self):
        return f"{self.category}/{self.subcategory}/{self.condition}/{self.image.name}"


class MergedSampleImage(TrackingModel):
    category = models.CharField(max_length=100)  # e.g., "internal"
    subcategory = models.CharField(max_length=100)  # e.g., "living_spaces"
    condition = models.CharField(max_length=100)  # e.g., "excellent"
    image = models.ImageField(upload_to="merged_sample_images/")
    quadrant_mapping = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "merged_sample_image"
        verbose_name = _("Merged Sample Image")
        verbose_name_plural = _("Merged Sample Images")
        # unique_together = ('category', 'subcategory', 'condition') # TODO: this might need to be changed


class ImageConditionAnalysis(TrackingModel):
    super_id = models.CharField(
        max_length=1028,
        null=True,
        blank=True,
        verbose_name=_("Super ID"),
    )
    image_url = models.URLField(null=True, blank=True, verbose_name=_("Image URL"))
    image_id = models.IntegerField(
        verbose_name=_("Image ID")
    )  # Keep as identifier within a property
    main_category = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("Main Category")
    )
    image_room_name = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("Image Room Name")
    )
    image_room_type = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("Image Room Type")
    )
    image_group_number = models.IntegerField(
        null=True, blank=True, verbose_name=_("Image Group Number")
    )
    merged_image_number = models.IntegerField(
        null=True, blank=True, verbose_name=_("Source Image Number")
    )
    merged_image_urls = models.JSONField(
        default=list, blank=True, verbose_name=_("Merged Image URLs")
    )
    similarity_image_excellent = models.FloatField(
        null=True, blank=True, verbose_name=_("Similarity Score: Excellent")
    )
    similarity_image_above_average = models.FloatField(
        null=True, blank=True, verbose_name=_("Similarity Score: Above Average")
    )
    similarity_image_below_average = models.FloatField(
        null=True, blank=True, verbose_name=_("Similarity Score: Below Average")
    )
    similarity_image_poor = models.FloatField(
        null=True, blank=True, verbose_name=_("Similarity Score: Poor")
    )
    image_condition_score = models.IntegerField(
        null=True, blank=True, verbose_name=_("Image Condition Score")
    )
    image_condition_label = models.CharField(
        max_length=50, null=True, blank=True, verbose_name=_("Image Condition Label")
    )
    image_condition_explanation = models.TextField(
        null=True, blank=True, verbose_name=_("Image Condition Explanation")
    )

    class Meta:
        db_table = "image_condition_analysis"  # Set DB table name
        verbose_name = _("Image Condition Analysis")
        verbose_name_plural = _("Image Condition Analyses")
        ordering = ["super_id", "image_id"]

    def __str__(self):
        return f"Image Condition Analysis for Image {self.image_id} of Super ID {self.super_id}"


class OverallImageAnalysis(TrackingModel):
    super_id = models.CharField(
        max_length=1028,
        null=True,
        blank=True,
        verbose_name=_("Super ID"),
    )
    property_url = models.URLField(
        null=True, blank=True, verbose_name=_("Property URL")
    )
    total_images_processed = models.IntegerField(
        null=True, blank=True, verbose_name=_("Total Images Processed")
    )
    distribution_images_excellent = models.FloatField(
        null=True, blank=True, verbose_name=_("Distribution: Excellent")
    )
    distribution_images_above_average = models.FloatField(
        null=True, blank=True, verbose_name=_("Distribution: Above Average")
    )
    distribution_images_below_average = models.FloatField(
        null=True, blank=True, verbose_name=_("Distribution: Below Average")
    )
    distribution_images_poor = models.FloatField(
        null=True, blank=True, verbose_name=_("Distribution: Poor")
    )
    overall_condition_score = models.FloatField(
        null=True, blank=True, verbose_name=_("Overall Condition Score")
    )
    overall_condition_label = models.CharField(
        max_length=50, null=True, blank=True, verbose_name=_("Overall Condition Label")
    )
    images_of_concern = models.IntegerField(
        null=True, blank=True, verbose_name=_("Images of Concern")
    )
    number_of_bedrooms = models.IntegerField(
        null=True, blank=True, verbose_name=_("Number of Bedrooms (Property)")
    )
    condition_confidence_beds = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name=_("Confidence Level: Bedrooms"),
    )
    condition_explanation = models.TextField(
        null=True, blank=True, verbose_name=_("Condition Explanation")
    )

    class Meta:
        db_table = "overall_image_analysis"  # Set DB table name
        verbose_name = _("Overall Image Analysis")
        verbose_name_plural = _("Overall Image Analyses")

    def __str__(self):
        # property_id here refers to the Property.primary_key value
        return f"Overall Analysis for Super ID {self.super_id}"


class AnalysisTask(TrackingModel):
    super_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, default="PENDING")
    progress = models.FloatField(default=0.0)
    stage = models.CharField(max_length=50, default="")
    stage_progress = models.JSONField(default=dict)
    notes = models.JSONField(default=dict, blank=True)
    trigger_analysis = models.BooleanField(default=True)

    class Meta:
        db_table = "analysis_task"
        ordering = ["-created_at"]

    def __str__(self):
        return f"AnalysisTask for Super ID {self.super_id} - Status: {self.status}"


class AnalysisEvent(TrackingModel):
    """Comprehensive event log for service interactions.

    Captures requests/responses/errors with payloads and metadata.
    """

    EVENT_TYPES = (
        ("REQUEST", "REQUEST"),
        ("RESPONSE", "RESPONSE"),
        ("ERROR", "ERROR"),
        ("PROGRESS", "PROGRESS"),
    )

    super_id = models.CharField(max_length=1028, db_index=True)
    event_type = models.CharField(max_length=32, choices=EVENT_TYPES)
    source = models.CharField(max_length=128, default="image_condition_service")
    target = models.CharField(max_length=256, blank=True, null=True)
    endpoint = models.CharField(max_length=512, blank=True, null=True)
    method = models.CharField(max_length=16, blank=True, null=True)
    http_status = models.IntegerField(blank=True, null=True)
    error_code = models.CharField(max_length=128, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    response_count = models.IntegerField(blank=True, null=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "analysis_event"
        indexes = [
            models.Index(fields=["super_id", "created_at"]),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.event_type} [{self.source} -> {self.target}] {self.endpoint} ({self.http_status})"
