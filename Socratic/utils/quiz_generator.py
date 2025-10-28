import random
import re
from django.utils import timezone
from ..models import ProcessingResult
from Quiz.models import Quiz, Question
from django.utils import timezone

class AIPoweredQuizGenerator:
    """
    Uses your existing AI processors to generate intelligent quizzes
    """
    
    @staticmethod
    def generate_quiz_from_processing_result(processing_result):
        """
        Generate quiz with AI-powered distractors and varied question types
        """
        try:
            qa_data = processing_result.questions_answers
            qa_pairs = qa_data.get('qa_pairs', [])
            summary = processing_result.summary
            
            if not qa_pairs:
                raise ValueError("No Q&A pairs available for quiz generation")
            
        
            all_answers = [qa.get('answer', '') for qa in qa_pairs if qa.get('answer')]
            
            # Create the quiz
            quiz = Quiz.objects.create(
                name=f"Quiz - {processing_result.document_title}",
                study_material=processing_result,
                total_questions=min(len(qa_pairs), 20),
                attempted=False,
                created_at=timezone.now()
            )
            
            # Generate questions with AI-powered enhancements
            for i, qa_pair in enumerate(qa_pairs[:20]):
                question_text = qa_pair.get('question', '')
                correct_answer = qa_pair.get('answer', '')
                
                if question_text and correct_answer:
                    # Use AI to generate intelligent distractors
                    options = AIPoweredQuizGenerator._generate_ai_distractors(
                        question_text, 
                        correct_answer,
                        summary,
                        processing_result.user.premium_user,
                        all_answers
                    )
                    
                    # Create the question
                    Question.objects.create(
                        quiz=quiz,
                        text=question_text,
                        answer=correct_answer,
                        option_1=options[0],
                        option_2=options[1],
                        option_3=options[2],
                        option_4=options[3],
                    )
            
            processing_result.quiz_generated = True
            processing_result.save()
            
            return quiz
            
        except Exception as e:
            print(f"Error generating quiz: {str(e)}")
            raise

    @staticmethod
    def _generate_ai_distractors(question, correct_answer, context, is_premium_user, all_answers=None): 
        """
        Use AI to generate intelligent, plausible distractors
        """
        try:
            # Choose the appropriate AI processor
            if is_premium_user:
                from .ai_processor import PremiumAIProcessor as AIProcessor
            else:
                from .free_ai_processor import AIProcessor
            
            # Generate distractors using AI
            distractors = AIPoweredQuizGenerator._get_ai_distractors(
                AIProcessor, question, correct_answer, context, all_answers 
            )
            
            # Ensure we have exactly 3 good distractors
            final_distractors = AIPoweredQuizGenerator._validate_distractors(
                distractors, correct_answer, question, all_answers 
            )
            
            # Combine and shuffle
            options = [correct_answer] + final_distractors
            random.shuffle(options)
            return options
            
        except Exception as e:
            print(f"AI distractor generation failed: {e}")
            # Fallback to improved non-AI method
            return AIPoweredQuizGenerator._generate_fallback_distractors(question, correct_answer, all_answers) 

    @staticmethod
    def _get_ai_distractors(ai_processor, question, correct_answer, context, all_answers=None): 
        
        """
        Use AI to generate plausible distractors
        """
        
        
        forbidden_list = ""
        if all_answers:
            
            forbidden_phrases = [f"- {ans[:150]}..." for ans in all_answers if ans.lower() != correct_answer.lower()]
            forbidden_list = "\n".join(forbidden_phrases)

        prompt = f"""
        Generate exactly 3 plausible but incorrect multiple choice options for this question.
        
        QUESTION: {question}
        CORRECT ANSWER: {correct_answer}
        CONTEXT: {context[:1000]}
        
        Requirements:
        1. Generate exactly 3 distractors
        2. Each distractor should be:
           - Related to the topic but factually wrong
           - Plausible enough to challenge someone who doesn't know the answer
           - Different from each other
           - Approximately the same length as the correct answer
        3. Format: One distractor per line, no numbering
        
        Examples of good distractors:
        - Common misconceptions
        - Related but different concepts
        - Partially correct but incomplete answers
        - Opposite or reversed concepts
        
        4. **CRITICAL REQUIREMENT:** Do NOT use any of the following phrases as distractors, as they are correct answers to other questions in this quiz. AVOID THEM:
        {forbidden_list if forbidden_list else "N/A"}
        """
        
        
        try:
            # Use your existing AI processor
            response = ai_processor._model.generate_content(prompt)
            if response.text:
                # Robustly parse the response, stripping list markers
                distractors = []
                for line in response.text.split('\n'):
                    cleaned_line = re.sub(r'^\s*([\d\w][\.\)]|[\-\*])\s*', '', line.strip()).strip()
                    
                    if cleaned_line: # Only add if the line isn't empty after stripping
                        distractors.append(cleaned_line)
                
                return distractors[:3] # Return the first 3 non-empty lines
        except Exception as e:
            print(f"AI distractor generation error: {e}")
        
        return []

    @staticmethod
    def _validate_distractors(distractors, correct_answer, question, all_answers=None): # <--- FIX: Add all_answers
        """
        Ensure distractors are valid and fallback if needed
        """
        valid_distractors = []
        
        # <--- FIX: Create a set of lowercased answers for efficient checking
        if all_answers is None:
            all_answers = []
        all_answers_lower = set(a.lower() for a in all_answers)
        correct_answer_lower = correct_answer.lower()
        # --- END FIX ---
        
        for distractor in distractors:
            distractor_lower = distractor.lower()
            # <--- FIX: Add check against all_answers_lower
            if (distractor and 
                distractor_lower != correct_answer_lower and 
                distractor_lower not in all_answers_lower and  # Check if it's another answer
                len(distractor) > 5 and 
                len(distractor) < 2000):
            # --- END FIX ---
                valid_distractors.append(distractor)
        
        # If we don't have enough good distractors, generate fallbacks
        while len(valid_distractors) < 3:
            fallback = AIPoweredQuizGenerator._create_fallback_distractor(
                correct_answer, len(valid_distractors)
            )
            # <--- FIX: Also check fallback against all answers
            if fallback not in valid_distractors and fallback.lower() not in all_answers_lower:
                valid_distractors.append(fallback)
            # --- END FIX ---
        
        return valid_distractors[:3]

    @staticmethod
    def _create_fallback_distractor(correct_answer, index):
        """
        Create structured fallback distractors when AI fails
        """
        fallback_strategies = [
            "A common misunderstanding of this concept",
            "Partially correct but misses key details",
            "Applies to a related but different concept",
            "The opposite of what is actually true",
            "An overgeneralization of the actual principle"
        ]
        
        base_length = min(50, len(correct_answer))
        strategy = fallback_strategies[index % len(fallback_strategies)]
        
        return f"{strategy} regarding this topic"

    @staticmethod
    def _generate_fallback_distractors(question, correct_answer, all_answers=None): # <--- FIX: Add all_answers
        """
        Improved non-AI fallback distractor generation
        """
        distractors = set()
        
        # <--- FIX: Create a set of lowercased answers for checking
        if all_answers is None:
            all_answers = []
        all_answers_lower = set(a.lower() for a in all_answers)
        # --- END FIX ---

        question_lower = question.lower()
        
        # Generate potential distractors
        potential_distractors = []
        if 'what is' in question_lower or 'define' in question_lower:
            potential_distractors.extend([
                "A common misconception about this term",
                "A related but different concept",
                "An oversimplified version of the definition"
            ])
        elif 'how' in question_lower or 'process' in question_lower:
            potential_distractors.extend([
                "A reversed order of the actual process",
                "Missing a crucial step in the process", 
                "Including an unnecessary or incorrect step"
            ])
        elif 'why' in question_lower:
            potential_distractors.extend([
                "A common but incorrect assumption",
                "Confusing cause and effect",
                "An effect rather than the cause"
            ])
        else:
            potential_distractors.extend([
                "A frequently mistaken alternative",
                "Partially correct but incomplete",
                "Based on common misunderstanding"
            ])
        
        # <--- FIX: Filter distractors against the all_answers list
        for d in potential_distractors:
            if d.lower() not in all_answers_lower:
                distractors.add(d)
        # --- END FIX ---
        
        distractor_list = list(distractors)
        while len(distractor_list) < 3:
            fallback = f"Alternative perspective {len(distractor_list) + 1}"
            if fallback.lower() not in all_answers_lower:
                distractor_list.append(fallback)
        
        options = [correct_answer] + distractor_list[:3]
        random.shuffle(options)
        return options
    

class AdvancedQuizGenerator(AIPoweredQuizGenerator):
    """
    Adds question type variety and difficulty levels
    """
    
    @staticmethod
    def generate_enhanced_quiz(processing_result):
        """
        Generate quiz with varied question types and difficulties
        """
        try:
            qa_data = processing_result.questions_answers
            qa_pairs = qa_data.get('qa_pairs', [])
            summary = processing_result.summary
            
            # <--- FIX: Get all answers to prevent them from being used as distractors
            all_answers = [qa.get('answer', '') for qa in qa_pairs if qa.get('answer')]
            
            NEW_MAX_QUESTIONS = 30
            QUESTIONS_PER_DIFFICULTY = 10
            
            quiz = Quiz.objects.create(
                name=f"Enhanced Quiz - {processing_result.document_title}",
                study_material=processing_result,
                total_questions=min(len(qa_pairs), NEW_MAX_QUESTIONS),
                attempted=False,
                created_at=timezone.now()
            )
            
            categorized_questions = AdvancedQuizGenerator._categorize_questions(qa_pairs)
            
            created_count = 0
            for difficulty in ['easy', 'medium', 'hard']:
                for qa_pair in categorized_questions.get(difficulty, [])[:QUESTIONS_PER_DIFFICULTY]:
                    if created_count >= NEW_MAX_QUESTIONS:
                        break
                        
                    AdvancedQuizGenerator._create_varied_question(
                        quiz, qa_pair, summary, 
                        processing_result.user.premium_user,
                        all_answers  # <--- FIX: Pass the list of all answers
                    )
                    created_count += 1
            
            quiz.total_questions = created_count
            quiz.save()
            
            processing_result.quiz_generated = True
            processing_result.save()
            
            return quiz
            
        except Exception as e:
            print(f"Error generating enhanced quiz: {str(e)}")
            raise

    @staticmethod
    def _categorize_questions(qa_pairs):
        """
        Categorize questions by estimated difficulty
        """
        categorized = {'easy': [], 'medium': [], 'hard': []}
        
        for qa_pair in qa_pairs:
            question = qa_pair.get('question', '')
            answer = qa_pair.get('answer', '')
            
            answer_length = len(answer.split())
            question_complexity = len(question.split())
            
            if answer_length < 20 and question_complexity < 10:
                categorized['easy'].append(qa_pair)
            elif answer_length > 50 or question_complexity > 20:
                categorized['hard'].append(qa_pair)
            else:
                categorized['medium'].append(qa_pair)
        
        return categorized

    @staticmethod
    def _create_varied_question(quiz, qa_pair, context, is_premium_user, all_answers=None): # <--- FIX: Add all_answers
        """
        Create different types of questions
        """
        question_text = qa_pair.get('question', '')
        correct_answer = qa_pair.get('answer', '')
        
        question_type = AdvancedQuizGenerator._determine_question_type(question_text, correct_answer)
        
        if question_type == "true_false" and len(correct_answer) < 100:
            AdvancedQuizGenerator._create_true_false_question(quiz, qa_pair)
        else:
            # Use the AI-powered multiple choice
            options = AIPoweredQuizGenerator._generate_ai_distractors(
                question_text, correct_answer, context, 
                is_premium_user, all_answers # <--- FIX: Pass all_answers
            )
            
            Question.objects.create(
                quiz=quiz,
                text=question_text,
                answer=correct_answer,
                option_1=options[0],
                option_2=options[1],
                option_3=options[2],
                option_4=options[3],
            )

    @staticmethod
    def _determine_question_type(question, answer):
        """
        Determine the best question type based on content
        """
        question_lower = question.lower()
        answer_lower = answer.lower()
        
        if any(word in question_lower for word in ['true', 'false', 'correct', 'incorrect']):
            return "true_false"
        return "multiple_choice"

    @staticmethod
    def _create_true_false_question(quiz, qa_pair):
        """
        Placeholder: Create a T/F question.
        This needs to be implemented.
        """
        question_text = qa_pair.get('question', '')
        correct_answer = qa_pair.get('answer', '')
        
        Question.objects.create(
            quiz=quiz,
            text=f"True or False: {question_text} - {correct_answer}",
            answer="True",
            option_1="True",
            option_2="False",
            option_3="N/A",
            option_4="N/A",
        )
        print(f"Warning: Using placeholder for _create_true_false_question")