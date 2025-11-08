from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import IntegrityError


class Command(BaseCommand):
    help = "Populates the database with dummy data"

    def handle(self, *args: Any, **options: Any) -> None:
        User = get_user_model()

        # Set your custom superuser data
        username: str = settings.ADMIN_USERNAME
        email: str = settings.ADMIN_EMAIL
        password: str = settings.ADMIN_PASSWORD
        phone: str = settings.ADMIN_PHONE

        try:
            # Attempt to create a new superuser
            User.objects.create_superuser(
                username=username, phone=phone, email=email, password=password
            )
            self.stdout.write(
                self.style.SUCCESS(f"Superuser {phone} created successfully")
            )
        except IntegrityError:
            self.stdout.write(self.style.WARNING(f"Superuser {phone} already exists"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {str(e)}"))

        self.stdout.write(
            self.style.SUCCESS("Successfully populated the database with dummy data")
        )
