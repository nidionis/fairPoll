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

    def is_valid(self):
        """Checks if the house contains at least 2 entities (Users or Sub-houses)"""
        total_entities = self.users.count() + self.parent_houses.count()
        return total_entities >= 2

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, House

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_active')
    search_fields = ('username', 'email')

@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_valid', 'created_at')
    search_fields = ('name',)
    filter_horizontal = ('users', 'parent_houses')

    def __str__(self):
        return self.name
