from .gemini_config import GeminiConfig

class PremiumAIProcessor:
    """
    Enhanced AI processor using Google Gemini
    """
    
    _model = None
    _models_loaded = False
    
    @classmethod
    def load_models(cls):
        """Load Gemini model"""
        if cls._models_loaded:
            return
            
        try:
            print("Loading Gemini model...")
            GeminiConfig.configure()
            cls._model = GeminiConfig.get_model("gemini-2.5-flash")
            cls._models_loaded = True
            print("Gemini model loaded successfully!")
        except Exception as e:
            print(f"Error loading Gemini model: {str(e)}")
            raise

    @classmethod
    def generate_enhanced_content(cls, study_text, past_questions_text=""):
        """
        Generate coherent summary and Q&A using Gemini
        """
        if not cls._models_loaded:
            cls.load_models()
        
        try:
            # Pre-process the text to ensure quality
            processed_text = cls._preprocess_study_text(study_text)
            
            if not processed_text or len(processed_text) < 100:
                return "Insufficient quality content for processing. Please ensure your document contains substantial text content.", []
            
            # Generate summary
            summary = cls._generate_coherent_summary(processed_text, past_questions_text)
            
            # Generate Q&A
            qa_data = cls._generate_meaningful_questions(processed_text, past_questions_text)
            
            return summary, qa_data
            
        except Exception as e:
            error_msg = f"Content generation failed: {str(e)}"
            return error_msg, {'error': error_msg}
    
    @classmethod
    def _preprocess_study_text(cls, text):
        """Ensure the text is suitable for processing"""
        if not text:
            return ""
        
        # Split into paragraphs and select the best ones
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # Filter for substantial paragraphs
        good_paragraphs = []
        for para in paragraphs:
            if len(para) >= 100 and len(para.split()) >= 15:
                good_paragraphs.append(para)
        

        selected_paragraphs = good_paragraphs[:15]
        
        if not selected_paragraphs:
            return text[:8000]  # Increased limit for Gemini
        
        return '\n\n'.join(selected_paragraphs)
    
    @classmethod
    def _generate_coherent_summary(cls, study_text, context_text):
        """Generate a coherent, well-structured summary using Gemini"""
        try:
            # Prepare prompt for summarization
            if context_text:
                prompt = f"""
                Please provide a comprehensive and well-structured summary of the following study material, 
                considering the context provided. Focus on key concepts, main ideas, and important details.

                STUDY MATERIAL:
                {study_text[:15000]}

                CONTEXT/PAST QUESTIONS:
                {context_text[:6000]}

                Please provide a clear, concise summary that highlights the most important information.
                """
            else:
                prompt = f"""
                Please provide a comprehensive and well-structured summary of the following study material.
                Focus on key concepts, main ideas, and important details.

                STUDY MATERIAL:
                {study_text[:15000]}

                Please provide a clear, concise summary that highlights the most important information.
                """
            
            # Generate summary using Gemini
            response = cls._model.generate_content(prompt)
            
            if response.text:
                summary = response.text.strip()
                # Ensure summary is adequate length
                if len(summary.split()) < 30:
                    # Fallback: create a basic summary from text
                    sentences = study_text.split('.')
                    key_sentences = [s.strip() for s in sentences[:4] if len(s.strip()) > 25]
                    summary = '. '.join(key_sentences) + '.'
                
                return summary
            else:
                return "Unable to generate summary at this time."
            
        except Exception as e:
            return f"Summary generation issue: {str(e)}"
    
    @classmethod
    def _generate_meaningful_questions(cls, study_text, context_text):
        """Generate meaningful, coherent Q&A pairs using Gemini"""
        try:
            # Prepare prompt for Q&A generation
            prompt = f"""
            Based on the following study material, generate 30-40 meaningful questions and answers 
            that test understanding of key concepts. The questions should be educational and 
            the answers should be comprehensive.

            STUDY MATERIAL:
            {study_text[:15000]}

            {f"CONTEXT/PAST QUESTIONS: {context_text[:6000]}" if context_text else ""}

            Please provide the output in this exact format for each question:

            Q1: [Question text]
            A1: [Comprehensive answer]

            Q2: [Question text]
            A2: [Comprehensive answer]

            ...and so on for 30-45 questions.

            Make sure questions cover different aspects of the material and answers are detailed.
            """
            
            response = cls._model.generate_content(prompt)
            
            if response.text:
                qa_pairs = cls._parse_qa_response(response.text)
                return {
                    'total_questions': len(qa_pairs),
                    'context_used': bool(context_text),
                    'qa_pairs': qa_pairs
                }
            else:
                return {
                    'total_questions': 0,
                    'context_used': bool(context_text),
                    'qa_pairs': [],
                    'message': 'Unable to generate questions at this time'
                }
            
        except Exception as e:
            return {
                'error': f"Q&A generation failed: {str(e)}",
                'total_questions': 0,
                'context_used': False,
                'qa_pairs': []
            }
    
    @classmethod
    def _parse_qa_response(cls, response_text):
        """Parse Gemini response into structured Q&A pairs"""
        qa_pairs = []
        lines = response_text.split('\n')
        
        current_question = None
        current_answer = []
        
        for line in lines:
            line = line.strip()
            if line.startswith(('Q', 'Question')) and ':' in line:
                # Save previous Q&A if exists
                if current_question and current_answer:
                    qa_pairs.append({
                        'id': len(qa_pairs) + 1,
                        'question': current_question,
                        'answer': ' '.join(current_answer).strip(),
                        'type': "concept_based",
                        'difficulty': "medium"
                    })
                
                # Start new question
                current_question = line.split(':', 1)[1].strip()
                current_answer = []
                
            elif line.startswith(('A', 'Answer')) and ':' in line:
                # Add to current answer
                answer_part = line.split(':', 1)[1].strip()
                current_answer.append(answer_part)
                
            elif current_question and line and not line.startswith(('Q', 'Question', 'A', 'Answer')):
                # Continuation of answer
                current_answer.append(line)
        
        # Add the last Q&A pair
        if current_question and current_answer:
            qa_pairs.append({
                'id': len(qa_pairs) + 1,
                'question': current_question,
                'answer': ' '.join(current_answer).strip(),
                'type': "concept_based",
                'difficulty': "medium"
            })
        
        # If parsing failed, create fallback questions
        if not qa_pairs:
            qa_pairs = cls._generate_fallback_questions(response_text)
        
        return qa_pairs[:40] # Limit to 40 questions
    
    @classmethod
    def _generate_fallback_questions(cls, text):
        """Generate fallback questions if parsing fails"""
        # Simple fallback - you can enhance this
        sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 30]
        
        qa_pairs = []
        for i, sentence in enumerate(sentences[:5]):
            words = sentence.split()
            if len(words) >= 8:
                concept = ' '.join(words[4:8])  # Extract a concept from the sentence
                qa_pairs.append({
                    'id': i + 1,
                    'question': f"Explain the concept of {concept}?",
                    'answer': sentence,
                    'type': "concept_based",
                    'difficulty': "medium"
                })
        
        return qa_pairs

    @classmethod
    def _extract_key_concepts(cls, text):
        """Extract meaningful concepts from text (fallback method)"""
        sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 40]
        
        concepts = []
        for sentence in sentences[:8]:
            words = sentence.split()
            if len(words) >= 5:
                concept_words = words[3:8]
                concept = ' '.join(concept_words)
                concepts.append((concept, sentence))
        
        return concepts[:5]