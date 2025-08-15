from django.core.management.base import BaseCommand
from image_condition_analysis.models import Prompt
from utils.prompts import labelling_prompt


class Command(BaseCommand):
    help = "Load or update the labelling prompt into the Prompt model"

    def handle(self, *args, **options):
        # You can adjust name/version to match your preference
        prompt_name = "labelling_prompt"
        version_num = 1

        prompt_obj, created = Prompt.objects.update_or_create(
            name=prompt_name,
            version=version_num,
            defaults={
                "content": labelling_prompt,
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created new Prompt record: {prompt_name} (v{version_num})"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Updated existing Prompt record: {prompt_name} (v{version_num})"
                )
            )
