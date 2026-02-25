from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, House

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_active')
    search_fields = ('username', 'email')

@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    filter_horizontal = ('users', 'parent_houses')

    def __str__(self):
        return self.name
