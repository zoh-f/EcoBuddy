from django.contrib import admin
from .models import Profile
# Register your models here.
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'display_name', 'joined_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'display_name')