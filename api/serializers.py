from rest_framework import serializers
from .models import Incident


class IncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Incident
        fields = [
            'id', 'dt', 'loc', 'inv', 'occ', 'dmg_raw',
            'alarm', 'sta', 'eng', 'by_user',
            'inj_c', 'inj_b', 'cas_c', 'cas_b', 'rem',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']