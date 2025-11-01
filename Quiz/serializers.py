from rest_framework import serializers
from .models import Quiz, Question, UserScore, UserAttempt, UserAnswer

class QuizSerializer(serializers.ModelSerializer):
    study_material = serializers.StringRelatedField()
    class Meta:
        model = Quiz
        fields = '__all__'

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        exclude = ['quiz',]

class QuizSubmissionSerializer(serializers.Serializer):
    answers = serializers.DictField(
        child=serializers.CharField(max_length=10000),
        help_text="Dictionary with question IDs as keys and selected options as values"
    )

class UserAttemptSerializer(serializers.ModelSerializer):
    quiz = serializers.StringRelatedField()
    class Meta:
        model = UserAttempt
        exclude = ['user',]