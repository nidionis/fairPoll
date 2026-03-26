from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model for the project.

    For now it behaves like Django's default user, but having this model
    lets us extend it later (roles, ticket bindings, etc.) without pain.
    """
    # Users belong to houses (membership).
    houses = models.ManyToManyField(
        "houses.House",
        blank=True,
        related_name="members",
    )

    # Simple plan flag used for quota rules (free: 1/day, paid: 10/day).
    PLAN_FREE = "free"
    PLAN_PAID = "paid"
    PLAN_CHOICES = [
        (PLAN_FREE, "Free"),
        (PLAN_PAID, "Paid"),
    ]
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default=PLAN_FREE)

    def __str__(self) -> str:
        return self.get_username()
