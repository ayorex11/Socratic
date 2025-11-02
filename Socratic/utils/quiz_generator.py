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
        Generate quiz with AI-generated answers and distractors
        """
        try:
            qa_data = processing_result.questions_answers
            qa_pairs = qa_data.get('qa_pairs', [])
            summary = processing_result.summary
            
            if not qa_pairs:
                raise ValueError("No Q&A pairs available for quiz generation")
            
            # Create the quiz
            quiz = Quiz.objects.create(
                name=f"Quiz - {processing_result.document_title}",
                study_material=processing_result,
                total_questions=min(len(qa_pairs), 20),
                attempted=False,
                created_at=timezone.now()
            )
            
            # Generate questions with AI-generated answers
            for i, qa_pair in enumerate(qa_pairs[:20]):
                question_text = qa_pair.get('question', '')
                
                if question_text:
                    # Generate new concise answer using AI
                    concise_answer = AIPoweredQuizGenerator._generate_concise_answer(
                        question_text,
                        summary,
                        processing_result.user.premium_user
                    )
                    
                    if concise_answer:
                        # Use AI to generate intelligent distractors
                        options = AIPoweredQuizGenerator._generate_ai_distractors(
                            question_text, 
                            concise_answer,
                            summary,
                            processing_result.user.premium_user
                        )

                        explanation = AIPoweredQuizGenerator._generate_explanation(
                            question_text,
                            concise_answer,
                            summary,
                            processing_result.user.premium_user
                        )
                        
                        # Create the question
                        Question.objects.create(
                            quiz=quiz,
                            text=question_text,
                            answer=concise_answer,
                            explanation=explanation,
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
    def _generate_concise_answer(question, context, is_premium_user):
        """
        Generate a short but detailed answer using AI
        """
        try:
            # Choose the appropriate AI processor
            if is_premium_user:
                from .ai_processor import PremiumAIProcessor as AIProcessor
            else:
                from .free_ai_processor import AIProcessor
            
            prompt = f"""
            Based on the context below, provide a SHORT but DETAILED answer to the question.
            
            QUESTION: {question}
            CONTEXT: {context[:1500]}
            
            Requirements for your answer:
            1. Keep it CONCISE (2-4 sentences maximum)
            2. Include key details but avoid unnecessary information
            3. Be accurate and factually correct based on the context
            4. Use clear, direct language
            5. Do NOT use phrases like "According to the context" or "Based on the text"
            6. Do NOT copy exact sentences from the context - paraphrase and summarize
            
            Format: Provide only the answer itself, no additional text.
            """
            
            response = AIProcessor._model.generate_content(prompt)
            if response.text:
                # Clean up the response
                answer = response.text.strip()
                # Remove any quotation marks or unwanted prefixes
                answer = re.sub(r'^["\']|["\']$', '', answer)
                # Ensure it's not too long
                if len(answer.split()) > 100:
                    # Truncate but maintain coherence
                    sentences = answer.split('. ')
                    if len(sentences) > 2:
                        answer = '. '.join(sentences[:2]) + '.'
                return answer
                
        except Exception as e:
            print(f"AI answer generation failed: {e}")
        
        # Fallback: generate a simple structured answer
        return AIPoweredQuizGenerator._generate_fallback_answer(question)

    @staticmethod
    def _generate_fallback_answer(question):
        """
        Generate a structured fallback answer when AI fails
        """
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['what is', 'define', 'meaning of']):
            return "A fundamental concept or term that represents the core idea being discussed, essential for understanding the broader context."
        elif any(word in question_lower for word in ['how does', 'how do', 'process']):
            return "This involves a systematic approach or series of steps that achieve the desired outcome through specific mechanisms and procedures."
        elif any(word in question_lower for word in ['why', 'purpose', 'reason']):
            return "The primary reason involves achieving specific objectives or addressing particular needs through established methods and principles."
        elif any(word in question_lower for word in ['benefit', 'advantage', 'importance']):
            return "Key advantages include improved efficiency, enhanced understanding, and better outcomes through systematic implementation."
        else:
            return "This involves important concepts and principles that contribute to overall understanding and effective application in relevant contexts."

    @staticmethod
    def _generate_ai_distractors(question, correct_answer, context, is_premium_user): 
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
                AIProcessor, question, correct_answer, context
            )
            
            # Ensure we have exactly 3 good distractors
            final_distractors = AIPoweredQuizGenerator._validate_distractors(
                distractors, correct_answer, question
            )
            
            # Combine and shuffle
            options = [correct_answer] + final_distractors
            random.shuffle(options)
            return options
            
        except Exception as e:
            print(f"AI distractor generation failed: {e}")
            # Fallback to improved non-AI method
            return AIPoweredQuizGenerator._generate_fallback_distractors(question, correct_answer)

    @staticmethod
    def _get_ai_distractors(ai_processor, question, correct_answer, context):
        """
        Use AI to generate plausible distractors
        """
        prompt = f"""
        Generate exactly 3 plausible but INCORRECT multiple choice options for this question.
        
        QUESTION: {question}
        CORRECT ANSWER: {correct_answer}
        CONTEXT: {context[:1000]}
        
        Requirements:
        1. Generate exactly 3 distractors
        2. Each distractor should be:
           - Related to the topic but factually wrong
           - Plausible enough to challenge someone who doesn't know the answer
           - Different from each other and from the correct answer
           - Approximately the same length as the correct answer (2-4 sentences)
           - Sound professional and credible but contain incorrect information
        3. Types of good distractors:
           - Common misconceptions about the topic
           - Related but different concepts from the same field
           - Partially correct but incomplete answers
           - Opposite or reversed versions of the correct concept
           - Overgeneralizations or oversimplifications
        
        4. Format: One distractor per line, no numbering or bullet points
        5. Make sure they are clearly different from: "{correct_answer}"
        """
        
        try:
            response = ai_processor._model.generate_content(prompt)
            if response.text:
                # Robustly parse the response
                distractors = []
                for line in response.text.split('\n'):
                    cleaned_line = re.sub(r'^\s*([\d\w][\.\)]|[\-\*])\s*', '', line.strip()).strip()
                    if cleaned_line and len(cleaned_line) > 10:  # Only add substantial lines
                        distractors.append(cleaned_line)
                
                return distractors[:3]
        except Exception as e:
            print(f"AI distractor generation error: {e}")
        
        return []

    @staticmethod
    def _validate_distractors(distractors, correct_answer, question):
        """
        Ensure distractors are valid and fallback if needed
        """
        valid_distractors = []
        correct_answer_lower = correct_answer.lower()
        
        for distractor in distractors:
            distractor_lower = distractor.lower()
            if (distractor and 
                distractor_lower != correct_answer_lower and
                len(distractor) > 10 and 
                len(distractor) < 500 and
                distractor not in valid_distractors):
                valid_distractors.append(distractor)
        
        # If we don't have enough good distractors, generate fallbacks
        while len(valid_distractors) < 3:
            fallback = AIPoweredQuizGenerator._create_fallback_distractor(
                correct_answer, len(valid_distractors)
            )
            if fallback not in valid_distractors:
                valid_distractors.append(fallback)
        
        return valid_distractors[:3]

    @staticmethod
    def _create_fallback_distractor(correct_answer, index):
        """
        Create structured fallback distractors when AI fails
        """
        fallback_strategies = [
            "This represents a common misunderstanding where people confuse related concepts in the field.",
            "While this seems plausible, it actually describes a different process or concept entirely.",
            "This answer contains partially correct information but misses crucial details and context.",
            "This describes the opposite of what actually occurs or represents a reversed perspective.",
            "This overgeneralizes the concept and fails to account for important specific factors.",
            "This applies to a related but fundamentally different principle in the same domain."
        ]
        
        return fallback_strategies[index % len(fallback_strategies)]

    @staticmethod
    def _generate_fallback_distractors(question, correct_answer):
        """
        Improved non-AI fallback distractor generation
        """
        distractors = set()
        
        question_lower = question.lower()
        
        # Generate context-appropriate distractors
        if 'what is' in question_lower or 'define' in question_lower:
            distractors.update([
                "This refers to a different but related concept that is often confused with the actual term.",
                "A common misconception that misinterprets the fundamental meaning of this concept.",
                "An oversimplified definition that misses key characteristics and applications."
            ])
        elif 'how' in question_lower or 'process' in question_lower:
            distractors.update([
                "This describes a reversed or incorrect sequence of the actual steps involved.",
                "A process that misses several crucial intermediate steps and decision points.",
                "An alternative method that is less efficient and produces different outcomes."
            ])
        elif 'why' in question_lower:
            distractors.update([
                "This confuses the actual causes with secondary effects or correlations.",
                "A common but incorrect assumption about the underlying reasons and motivations.",
                "This describes symptoms rather than addressing the fundamental causes."
            ])
        elif 'benefit' in question_lower or 'advantage' in question_lower:
            distractors.update([
                "These are actually disadvantages or limitations of the approach being discussed.",
                "Benefits that apply to a different method or system entirely.",
                "Exaggerated claims that aren't supported by evidence or practical experience."
            ])
        else:
            distractors.update([
                "A frequently mistaken interpretation that contradicts established knowledge.",
                "Partially correct information combined with significant factual errors.",
                "An answer that applies to different circumstances or boundary conditions."
            ])
        
        distractor_list = list(distractors)
        while len(distractor_list) < 3:
            fallback = f"This represents alternative perspective {len(distractor_list) + 1} with limited applicability."
            distractor_list.append(fallback)
        
        options = [correct_answer] + distractor_list[:3]
        random.shuffle(options)
        return options
    
    @staticmethod
    def _generate_explanation(question, correct_answer, context, is_premium_user):
        """
        Generate a brief explanation for the correct answer using AI
        """
        try:
            # Choose the appropriate AI processor
            if is_premium_user:
                from .ai_processor import PremiumAIProcessor as AIProcessor
            else:
                from .free_ai_processor import AIProcessor
            
            prompt = f"""
            Provide a brief explanation (1-3 sentences) for why the following answer is correct based on the context.
            
            QUESTION: {question}
            CORRECT ANSWER: {correct_answer}
            CONTEXT: {context[:1500]}
            
            Requirements:
            1. Keep it concise and to the point
            2. Clearly link the explanation to the context provided
            3. Avoid unnecessary details or tangents
            
            Format: Provide only the explanation itself, no additional text.
            """
            
            response = AIProcessor._model.generate_content(prompt)
            if response.text:
                explanation = response.text.strip()
                return explanation
                
        except Exception as e:
            print(f"AI explanation generation failed: {e}")
        
        return "This answer is correct based on established knowledge and principles related to the topic."


class AdvancedQuizGenerator(AIPoweredQuizGenerator):
    """
    Adds question type variety and difficulty levels with AI-generated answers
    """
    
    @staticmethod
    def generate_enhanced_quiz(processing_result):
        """
        Generate quiz with varied question types, difficulties, and AI-generated answers
        """
        try:
            qa_data = processing_result.questions_answers
            qa_pairs = qa_data.get('qa_pairs', [])
            summary = processing_result.summary
            
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
                        processing_result.user.premium_user
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
        Categorize questions by estimated difficulty based on question complexity
        """
        categorized = {'easy': [], 'medium': [], 'hard': []}
        
        for qa_pair in qa_pairs:
            question = qa_pair.get('question', '')
            
            question_complexity = len(question.split())
            has_complex_terms = any(term in question.lower() for term in [
                'analyze', 'evaluate', 'critique', 'compare', 'contrast', 'synthesize'
            ])
            
            if question_complexity < 8 and not has_complex_terms:
                categorized['easy'].append(qa_pair)
            elif question_complexity > 15 or has_complex_terms:
                categorized['hard'].append(qa_pair)
            else:
                categorized['medium'].append(qa_pair)
        
        return categorized

    @staticmethod
    def _create_varied_question(quiz, qa_pair, context, is_premium_user):
        """
        Create different types of questions with AI-generated answers
        """
        question_text = qa_pair.get('question', '')
        
        # Always generate a new concise answer
        concise_answer = AIPoweredQuizGenerator._generate_concise_answer(
            question_text, context, is_premium_user
        )
        
        if not concise_answer:
            return
            
        question_type = AdvancedQuizGenerator._determine_question_type(question_text, concise_answer)
        
        if question_type == "true_false" and len(concise_answer) < 100:
            AdvancedQuizGenerator._create_true_false_question(quiz, question_text, concise_answer)
        else:
            # Use the AI-powered multiple choice
            options = AIPoweredQuizGenerator._generate_ai_distractors(
                question_text, concise_answer, context, is_premium_user
            )
            
            Question.objects.create(
                quiz=quiz,
                text=question_text,
                answer=concise_answer,
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
        
        # Use true/false for factual statements that can be verified
        if any(phrase in question_lower for phrase in [
            'true or false', 'correct or incorrect', 'accurate statement',
            'valid statement', 'factually correct'
        ]):
            return "true_false"
        return "multiple_choice"

    @staticmethod
    def _create_true_false_question(quiz, question_text, correct_answer):
        """
        Create a True/False question with AI-generated content
        """
        # For T/F questions, we need to frame them as statements
        statement = question_text
        
        Question.objects.create(
            quiz=quiz,
            text=f"True or False: {statement}",
            answer="True",  # Assuming the generated answer makes it true
            option_1="True",
            option_2="False",
            option_3="Partially True",
            option_4="Cannot be determined",
        )

