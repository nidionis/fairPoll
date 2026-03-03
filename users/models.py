from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model for the project.

    For now it behaves like Django's default user, but having this model
    lets us extend it later (roles, ticket bindings, etc.) without pain.
    """

    # Example extension point (disabled for now):
    # house = models.ForeignKey("houses.House", null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self) -> str:
        return self.get_username()
