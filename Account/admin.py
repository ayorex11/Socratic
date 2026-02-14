from django.contrib import admin
from .models import User, UserFingerprint

# Register your models here.
admin.site.register(User)
admin.site.register(UserFingerprint)
