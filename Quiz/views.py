from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import F # New Import for atomic updates
from .models import Quiz, Question, UserScore, AttemptTracker, UserAnswer, UserAttempt
from .serializers import QuizSerializer, QuestionSerializer, QuizSubmissionSerializer, UserAttemptSerializer
from logs.models import LogEntry
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
import re
import unicodedata
from Socratic.models import ProcessingResult # New Import for comprehensive text cleaning

# --- Utility Function: Aggressive Text Normalization ---
def normalize_text_for_comparison(text):
    """
    Aggressively standardizes text for comparison by removing all
    formatting, special characters, and reducing all whitespace.
    """
    if not isinstance(text, str):
        return ""
    
    # 1. Normalize Unicode form (NFKC is great for standardizing non-standard spaces/chars)
    text = unicodedata.normalize('NFKC', text)
    
    # 2. Lowercase and strip
    text = text.strip().lower()
    
    # 3. Handle non-standard spaces explicitly
    text = text.replace('\xa0', ' ') 
    text = text.replace(' ', ' ')
    
    # 4. Aggressive Markdown/Special Character removal (removes **, *, and escaped quotes \")
    text = re.sub(r'\*\*|\*|\\"', '', text) 
    
    # 5. Replace ALL sequences of whitespace (including newlines/tabs/multiple spaces) with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # 6. Final strip
    text = text.strip()
    
    return text

# --- View Functions ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_quizzes(request):
    user = request.user
    quizzes = Quiz.objects.filter(study_material__user=user)
    serializer = QuizSerializer(quizzes, many=True)
    LogEntry.objects.create(
        user=user, 
        timestamp=timezone.now(),
        level = 'Normal',
        status_code = '200',
        message = f'User {user.username} retrieved their quizzes successfully.'
    )
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def start_quiz(request, pk):
    """
    pk is now the processing_result_id (not quiz_id)
    Users can access:
    - Their own quizzes
    - Other free users' quizzes (if they're free)
    - All quizzes (if they're premium)
    """
    user = request.user
    try:
        # Get the processing result
        result = ProcessingResult.objects.get(id=pk)
        
        # Check access permissions
        if result.user != user:
            # Not their own document - check community access
            if not user.is_premium_active and result.user.is_premium_active:
                LogEntry.objects.create(
                    user=user, 
                    timestamp=timezone.now(),
                    level='Medium',
                    status_code='403',
                    message=f'User {user.username} attempted to access premium quiz {pk} without subscription.'
                )
                return Response(
                    {'error': 'Premium subscription required to access this quiz.'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Get the quiz for this processing result
        quiz = Quiz.objects.get(study_material=result)
        
        # Only reset score/answers for own quizzes
        if result.user == user:
            try: 
                score = UserScore.objects.get(user=user, quiz=quiz)
                score.score = 0
                score.save()
            except UserScore.DoesNotExist:
                UserScore.objects.create(user=user, quiz=quiz, score=0)
                
            # Clear previous answers only for own quiz
            UserAnswer.objects.filter(user=user, question__quiz=quiz).delete()
        
        questions = Question.objects.filter(quiz=quiz)
        serializer = QuestionSerializer(questions, many=True)
        
        LogEntry.objects.create(
            user=user, 
            timestamp=timezone.now(),
            level='Normal',
            status_code='200',
            message=f'User {user.username} started quiz for processing result {pk}.'
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except ProcessingResult.DoesNotExist:
        LogEntry.objects.create(
            user=user, 
            timestamp=timezone.now(),
            level='Medium',
            status_code='404',
            message=f'User {user.username} attempted to start quiz for non-existent processing result {pk}.'
        )
        return Response({'error': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)
        
    except Quiz.DoesNotExist:
        LogEntry.objects.create(
            user=user, 
            timestamp=timezone.now(),
            level='Medium',
            status_code='404',
            message=f'User {user.username} attempted to start non-existent quiz for processing result {pk}.'
        )
        return Response({'error': 'Quiz not found for this document.'}, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        LogEntry.objects.create(
            user=user, 
            timestamp=timezone.now(),
            level='Error',
            status_code='500',
            message=f'Critical server error during quiz start for processing result {pk}: {str(e)}'
        )
        return Response({'error': 'An internal server error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_answer(request, pk):
    """
    pk is processing_result_id
    Only allow submissions for own quizzes OR community quizzes with proper access
    """
    user = request.user
    
    serializer = QuizSubmissionSerializer(data=request.data)
    if not serializer.is_valid():
        LogEntry.objects.create(
            user=user, 
            timestamp=timezone.now(),
            level='Medium',
            status_code='400',
            message=f'User {user.username} submitted invalid data for processing result {pk}: {serializer.errors}'
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    validated_data = serializer.validated_data
    answers = validated_data.get('answers', {})
    score = 0
    
    try:
        # Get processing result
        result = ProcessingResult.objects.get(id=pk)
        
        # Check access permissions
        if result.user != user:
            if not user.is_premium_active and result.user.is_premium_active:
                return Response(
                    {'error': 'Premium subscription required to access this quiz.'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        
        quiz = Quiz.objects.get(study_material=result)
        total_questions = quiz.total_questions
        
        # Process all answers
        for question_id_str, selected_option in answers.items():
            try:
                question_id = int(question_id_str)
            except ValueError:
                LogEntry.objects.create(
                    user=user, level='Warning', status_code='400',
                    message=f'Invalid question ID format skipped: {question_id_str}'
                )
                continue
            
            try:
                question = Question.objects.get(id=question_id, quiz=quiz)
                
                # Record user answer
                UserAnswer.objects.update_or_create(
                    user=user,
                    question=question,
                    defaults={'selected_option': selected_option}
                )
                
                # Compare using normalization
                normalized_correct = normalize_text_for_comparison(question.answer)
                normalized_selected = normalize_text_for_comparison(selected_option)
                
                if normalized_correct == normalized_selected:
                    score += 1
                    
            except Question.DoesNotExist:
                continue
        
        # Update final score
        UserScore.objects.update_or_create(
            user=user, 
            quiz=quiz,
            defaults={'score': score}
        )
        
        # Track attempt using F() for atomic increment
        attempt_tracker, created = AttemptTracker.objects.get_or_create(
            user=user, 
            quiz=quiz,
            defaults={'number_of_questions': total_questions}
        )
        AttemptTracker.objects.filter(pk=attempt_tracker.pk).update(attempts=F('attempts') + 1)
        
        # Calculate percentage
        percentage = (score / total_questions * 100) if total_questions > 0 else 0
        is_passed = percentage >= 70
        
        # Record final attempt
        UserAttempt.objects.create(
            user=user, 
            quiz=quiz, 
            score=score,
            is_passed=is_passed
        )
        
        # Only mark as attempted for own quizzes
        if result.user == user and not quiz.attempted:
            quiz.attempted = True
            quiz.save()
        
        LogEntry.objects.create(
            user=user, 
            timestamp=timezone.now(),
            level='Normal',
            status_code='200',
            message=f'User {user.username} submitted quiz for processing result {pk} with score {score}/{total_questions}.'
        )
        
        return Response({
            'score': score,
            'total_questions': total_questions,
            'percentage': percentage,
            'is_passed': is_passed
        })
        
    except ProcessingResult.DoesNotExist:
        LogEntry.objects.create(
            user=user, 
            timestamp=timezone.now(),
            level='Medium',
            status_code='404',
            message=f'User {user.username} attempted to submit for non-existent processing result {pk}.'
        )
        return Response({'error': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)
        
    except Quiz.DoesNotExist:
        LogEntry.objects.create(
            user=user, 
            timestamp=timezone.now(),
            level='Medium',
            status_code='404',
            message=f'User {user.username} attempted to submit non-existent quiz for processing result {pk}.'
        )
        return Response({'error': 'Quiz not found.'}, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        LogEntry.objects.create(
            user=user, 
            timestamp=timezone.now(),
            level='Error',
            status_code='500',
            message=f'Critical server error during quiz submission for processing result {pk}: {str(e)}'
        )
        return Response({'error': 'An internal server error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_attempts(request, pk):
    """
    pk is processing_result_id
    Only show attempts for the current user (regardless of document owner)
    """
    user = request.user
    try:
        result = ProcessingResult.objects.get(id=pk)
        
        # Check access
        if result.user != user:
            if not user.is_premium_active and result.user.is_premium_active:
                return Response(
                    {'error': 'Premium subscription required.'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        
        quiz = Quiz.objects.get(study_material=result)
        
        # Only get THIS user's attempts
        attempts = UserAttempt.objects.filter(user=user, quiz=quiz)
        
        try:
            tracker = AttemptTracker.objects.get(user=user, quiz=quiz)
            total_attempts = tracker.attempts
        except AttemptTracker.DoesNotExist:
            total_attempts = 0
        
        serializer = UserAttemptSerializer(attempts, many=True)
        
        LogEntry.objects.create(
            user=user, 
            timestamp=timezone.now(),
            level='Normal',
            status_code='200',
            message=f'User {user.username} retrieved attempts for processing result {pk}.'
        )
        
        data = {
            'total_attempts': total_attempts,
            'attempts': serializer.data
        }
        return Response(data, status=status.HTTP_200_OK)
        
    except ProcessingResult.DoesNotExist:
        return Response({'error': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)
        
    except Quiz.DoesNotExist:
        return Response({'error': 'Quiz not found.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])    
def get_all_attempts(request):
    user = request.user
    try:
        attempts = UserAttempt.objects.filter(user=user)
        serializer = UserAttemptSerializer(attempts, many=True)
        LogEntry.objects.create(
            user=user, 
            timestamp=timezone.now(),
            level='Normal',
            status_code='200',
            message=f'User {user.username} retrieved all attempts.'
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Quiz.DoesNotExist:
        LogEntry.objects.create(
            user=user, 
            timestamp=timezone.now(),
            level='Medium',
            status_code='404',
            message=f'User {user.username} attempted to retrieve all attempts.'
        )
        return Response({'error': 'Attempts not found.'}, status=status.HTTP_404_NOT_FOUND)