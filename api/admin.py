from django.contrib import admin
from .models import Incident, OTPRequest


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display  = ('id', 'dt', 'loc', 'inv', 'alarm', 'dmg_raw', 'by_user', 'created_at')
    list_filter   = ('inv', 'alarm')
    search_fields = ('loc', 'occ', 'by_user', 'rem')


@admin.register(OTPRequest)
class OTPRequestAdmin(admin.ModelAdmin):
    list_display = ('email', 'otp', 'created_at', 'is_used')
    list_filter  = ('is_used',)