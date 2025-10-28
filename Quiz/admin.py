from django.contrib import admin
from .models import Quiz, Question, UserScore, UserAttempt, AttemptTracker, UserAnswer
admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(UserScore)
admin.site.register(UserAttempt)
admin.site.register(AttemptTracker)
admin.site.register(UserAnswer)
