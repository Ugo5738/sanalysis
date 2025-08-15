from django.apps import AppConfig


class ImageConditionAnalysisConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "image_condition_analysis"

    def ready(self):
        # Import the signals module to ensure signal handlers are registered.
        import image_condition_analysis.signals

        print("Image Condition Analysis signals have been imported and registered.")
