from django.conf import settings
from django.db import models


class House(models.Model):
    name = models.CharField(max_length=255)

    # A house does NOT belong to a user, but it has a creator (audit trail).
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_houses",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name
