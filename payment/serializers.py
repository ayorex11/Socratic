from rest_framework import serializers

def is_positive(value):
    if value <= 0:
        raise serializers.ValidationError("Amount must be positive.")
    return value

class DepositSerializer(serializers.Serializer):

    amount = serializers.IntegerField(validators=[is_positive])
    email = serializers.EmailField()
    pricing = serializers.IntegerField()