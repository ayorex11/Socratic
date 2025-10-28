from django.db import models
from Account.models import User
from Socratic.models import ProcessingResult
class Quiz(models.Model):
    name = models.CharField(max_length=100)
    study_material = models.ForeignKey(ProcessingResult, on_delete=models.CASCADE, related_name='quizzes')
    total_questions = models.IntegerField(default=0)
    attempted = models.BooleanField(default=False)
    created_at = models.DateTimeField(blank= True, null= True, auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name
    

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    text = models.TextField()
    answer = models.TextField()
    option_1 = models.TextField()
    option_2 = models.TextField()
    option_3 = models.TextField()
    option_4 = models.TextField()



    def __str__(self):
        return self.text

class UserScore(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField()

    def __str__(self):
        return f"{self.user.username} - {self.quiz.name} - {self.score}"
    
class AttemptTracker(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    number_of_questions = models.IntegerField()
    attempts = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} - {self.quiz.name} - {self.attempts} attempts"
    
class UserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=1000)


    def __str__(self):
        return f"{self.user.username} - {self.question.text}"
    

class UserAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField()
    date_taken = models.DateTimeField(auto_now_add=True)
    is_passed = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.user.username} - {self.quiz.name} - {self.score}"