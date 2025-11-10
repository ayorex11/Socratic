from django.db import models
from Account.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal

class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False, related_name='user_transaction')
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    type_of_transaction = models.CharField(max_length=250, default='Payment', blank=False, null=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_completed = models.DateTimeField(blank=False, null=True)
    completed = models.BooleanField(default=False)
    reference = models.CharField(max_length=50, blank=False, null=False)

    def __str__(self):
        return self.user.username + " - " + str(self.amount_paid) + " - " + self.type_of_transaction + " - " + str(self.completed)

