from rest_framework import serializers
from Account.utils import is_student_email
from decimal import Decimal

# Valid plan amounts (using Decimal for precision)
STUDENT_PLAN_AMOUNT = Decimal('3000.00')
PREMIUM_PLAN_AMOUNT = Decimal('7500.00')

def validate_plan_amount(value):
    """
    Validate that the amount is exactly one of the valid plan amounts.
    Only 3000 (student) or 7500 (premium) are allowed.
    """
    if value <= 0:
        raise serializers.ValidationError("Amount must be positive.")
    
    if value not in [STUDENT_PLAN_AMOUNT, PREMIUM_PLAN_AMOUNT]:
        raise serializers.ValidationError(
            f"Invalid amount. Only Student Plan ({STUDENT_PLAN_AMOUNT}) or Premium Plan ({PREMIUM_PLAN_AMOUNT}) are allowed."
        )
    
    return value

class DepositSerializer(serializers.Serializer):
    amount = serializers.IntegerField(validators=[validate_plan_amount])
    email = serializers.EmailField()
    
    def validate(self, data):
        """
        Validate that student plan (3000) is only available to users with student emails.
        Premium plan (7500) is available to everyone.
        """
        amount = data.get('amount')
        email = data.get('email')
        
        # If user is trying to pay for student plan, verify they have a student email
        if amount == STUDENT_PLAN_AMOUNT:
            if not is_student_email(email):
                raise serializers.ValidationError({
                    'amount': f'Student Plan ({STUDENT_PLAN_AMOUNT}) requires a student/educational email address. '
                              f'Please use a university, college, or school email, or select Premium Plan ({PREMIUM_PLAN_AMOUNT}).'
                })
        
        return data