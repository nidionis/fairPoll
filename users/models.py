from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Nous pourrons ajouter des champs spécifiques ici plus tard si besoin
    # (ex: public_key, etc.)
    
    def __str__(self):
        return self.username


class House(models.Model):
    name = models.CharField(max_length=255)
    users = models.ManyToManyField(User, related_name="houses", blank=True)
    parent_houses = models.ManyToManyField(
        "self",
        symmetrical=False,
        related_name="sub_houses",
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
