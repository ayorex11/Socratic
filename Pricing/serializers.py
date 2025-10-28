from rest_framework import serializers
from .models import Pricing

class PricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pricing
        fields = '__all__'
        read_only_fields = ['user_count', ]

