from django.urls import path
from . import views

urlpatterns = [
    path('quizzes/', views.get_user_quizzes, name='get_user_quizzes'),
    path('quizzes/<int:quiz_id>/start/', views.start_quiz, name='start_quiz'),
    path('quizzes/<int:quiz_id>/submit/', views.submit_answer, name='submit_answer'),
    path('quizzes/<int:quiz_id>/attempts/', views.get_my_attempts, name='get_user_attempts'),
    path('quizzes/attempts/all/', views.get_all_attempts, name='get_all_user_attempts'),
]