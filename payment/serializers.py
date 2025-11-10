from rest_framework import serializers

def is_positive(value):
    if value <= 0:
        raise serializers.ValidationError("Amount must be positive.")
    elif value < 7500:
        raise serializers.ValidationError("Minimum deposit amount is 7500.")
    return value

class DepositSerializer(serializers.Serializer):

    amount = serializers.IntegerField(validators=[is_positive])
    email = serializers.EmailField()