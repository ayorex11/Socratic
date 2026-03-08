from .gemini_config import GeminiConfig

# ── Prompt templates ────────────────────────────────────────────────────────

_SUMMARY_WITH_CONTEXT = """
You are a university lecturer creating a comprehensive study summary for students.

Your task is to summarize the ENTIRE document below. Do NOT skip any section.
Work through the material systematically from start to finish.

RULES:
- Cover EVERY topic, heading, and concept in the document — nothing is optional
- For each major section, write a clear paragraph or set of bullet points
- Use the exact terminology from the document (students are tested on specific terms)
- Include all definitions, lists, classifications, and named techniques
- Preserve numbered lists exactly as they appear (e.g. "3 benefits of X", "4 types of Y")
- Flag every named concept, term, framework, method, or tool introduced in the document
- Format with clear headings that MATCH the document's own section headings
- If the document has 10 sections, your summary must cover all 10

OUTPUT FORMAT:
Use markdown with ## headings for major sections, ### for sub-sections.
Under each heading, use bullet points for key facts and definitions.
End with a "Key Terms to Know" section listing every named concept.

STUDY MATERIAL (cover it all — page by page, section by section):
{study_text}

PAST QUESTIONS (use these to understand what the examiner focuses on — ensure those topics are well covered in the summary):
{context_text}

Write the complete, section-by-section summary now:
"""

_SUMMARY_NO_CONTEXT = """
You are a university lecturer creating a comprehensive study summary for students.

Your task is to summarize the ENTIRE document below. Do NOT skip any section.
Work through the material systematically from start to finish.

RULES:
- Cover EVERY topic, heading, and concept in the document — nothing is optional
- For each major section, write a clear paragraph or set of bullet points
- Use the exact terminology from the document (students are tested on specific terms)
- Include all definitions, lists, classifications, and named techniques
- Preserve numbered lists exactly as they appear (e.g. "3 benefits of X", "4 types of Y")
- Flag every named concept, term, framework, method, or tool introduced in the document
- Format with clear headings that MATCH the document's own section headings
- If the document has 10 sections, your summary must cover all 10

OUTPUT FORMAT:
Use markdown with ## headings for major sections, ### for sub-sections.
Under each heading, use bullet points for key facts and definitions.
End with a "Key Terms to Know" section listing every named concept.

STUDY MATERIAL (cover it all — page by page, section by section):
{study_text}

Write the complete, section-by-section summary now:
"""

_QA_WITH_CONTEXT = """
You are a university exam setter. Generate {num_questions} exam-style questions and model your question style EXACTLY after the past questions provided.

QUESTION STYLE RULES (critical — follow these strictly):
- Use imperative verbs: "State", "List", "Define", "Explain", "Describe", "What is", "How does", "Why is"
- Be SPECIFIC and DIRECT — not vague (e.g. "State 3 benefits of X" not "Discuss X")
- When the material gives a specific count, include it (e.g. "State 4 challenges...", "List 5 types...")
- Mix question types: definitions (25%), list/enumeration (30%), explanation (30%), comparison (15%)
- Draw questions from EVERY section of the document — spread evenly, start to finish
- Never cluster more than 2 questions on the same topic
- Answers must be complete and use the exact terms from the material

MANDATORY COVERAGE — every one of these must appear as at least one question:
- All named concepts, methods, frameworks, or tools introduced in the material
- All numbered lists in the material (benefits, steps, types, categories, use cases, etc.)
- Definitions of all key terms introduced in the material
- Any comparisons or distinctions the material draws between two or more things

PAST QUESTIONS — mirror this exact style and level:
{context_text}

STUDY MATERIAL:
{study_text}

OUTPUT FORMAT — use exactly this pattern for EVERY question (no deviation):

Q1: [Question]
A1: [Answer]

Q2: [Question]
A2: [Answer]

...continue for all {num_questions} questions.
"""

_QA_NO_CONTEXT = """
You are a university exam setter. Generate {num_questions} exam-style questions from the study material below.

QUESTION STYLE RULES (critical — follow these strictly):
- Use imperative verbs: "State", "List", "Define", "Explain", "Describe", "What is", "How does", "Why is"
- Be SPECIFIC and DIRECT — not vague (e.g. "State 3 benefits of X" not "Discuss X")
- When the material gives a specific count, include it (e.g. "State 4 challenges...", "List 5 types...")
- Mix question types: definitions (25%), list/enumeration (30%), explanation (30%), comparison (15%)
- Draw questions from EVERY section of the document — spread evenly, start to finish
- Never cluster more than 2 questions on the same topic
- Answers must be complete and use the exact terms from the material

MANDATORY COVERAGE — every one of these must appear as at least one question:
- All named concepts, methods, frameworks, or tools introduced in the material
- All numbered lists in the material (benefits, steps, types, categories, use cases, etc.)
- Definitions of all key terms introduced in the material
- Any comparisons or distinctions the material draws between two or more things

ORDER: Start with foundational definitions → move to processes and mechanisms → end with applications and edge cases.

STUDY MATERIAL:
{study_text}

OUTPUT FORMAT — use exactly this pattern for EVERY question (no deviation):

Q1: [Question]
A1: [Answer]

Q2: [Question]
A2: [Answer]

...continue for all {num_questions} questions.
"""

_FLASHCARD = """
You are creating exam flashcards for a university student.

Extract {num_cards} key terms from the study material below.

SELECTION RULES:
- Prioritise: named concepts, frameworks, methods, tools, defined acronyms, and items from numbered lists
- Include terms a student MUST know by name for an exam
- Each definition must be 1–3 sentences — concise enough for a physical flashcard
- Use the exact definition wording from the material wherever possible

STUDY MATERIAL:
{study_text}

OUTPUT FORMAT — use exactly this pattern:

TERM: [Term or acronym]
DEFINITION: [Concise exam-ready definition]

TERM: [Term or acronym]
DEFINITION: [Concise exam-ready definition]

...continue for all {num_cards} terms.
"""


# ── Processor ────────────────────────────────────────────────────────────────

class PremiumAIProcessor:
    """
    Enhanced AI processor using Google Gemini with full context window support.
    Generates comprehensive, exam-aligned summaries and questions.
    """

    _model = None
    _models_loaded = False

    # ── Config ────────────────────────────────────────────────────────────

    NUM_QUESTIONS = 35       # questions per document
    NUM_FLASHCARDS = 20      # flashcard terms
    MAX_STUDY_CHARS = 200_000
    MAX_CONTEXT_CHARS = 50_000

    # ── Lifecycle ─────────────────────────────────────────────────────────

    @classmethod
    def load_models(cls):
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

    # ── Public API ────────────────────────────────────────────────────────

    @classmethod
    def generate_enhanced_content(cls, study_text, past_questions_text=""):
        """Generate summary and Q&A using Gemini."""
        if not cls._models_loaded:
            cls.load_models()

        try:
            processed_text = cls._preprocess_study_text(study_text)

            if not processed_text or len(processed_text) < 100:
                return (
                    "Insufficient quality content for processing. "
                    "Please ensure your document contains substantial text content.",
                    []
                )

            summary = cls._generate_coherent_summary(processed_text, past_questions_text)
            qa_data = cls._generate_meaningful_questions(processed_text, past_questions_text)

            return summary, qa_data

        except Exception as e:
            error_msg = f"Content generation failed: {str(e)}"
            return error_msg, {"error": error_msg}

    @classmethod
    def generate_flashcards(cls, study_text):
        """Generate flashcard term/definition pairs using Gemini."""
        if not cls._models_loaded:
            cls.load_models()

        try:
            processed_text = cls._preprocess_study_text(study_text)
            prompt = _FLASHCARD.format(
                num_cards=cls.NUM_FLASHCARDS,
                study_text=processed_text[:cls.MAX_STUDY_CHARS],
            )
            response = cls._model.generate_content(prompt)
            if response.text:
                return cls._parse_flashcards_response(response.text)
            return []
        except Exception as e:
            print(f"Flashcard generation failed: {str(e)}")
            return []

    # ── Private helpers ───────────────────────────────────────────────────

    @classmethod
    def _preprocess_study_text(cls, text):
        """
        Return the full usable text — no artificial paragraph limits.
        Gemini 2.5 Flash supports ~1 M tokens; a 100-page PDF is well within limits.
        """
        if not text:
            return ""

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        good = [p for p in paragraphs if len(p) >= 100 and len(p.split()) >= 15]

        if not good:
            return text[:500_000]

        return "\n\n".join(good)  # NO limit — send everything

    @classmethod
    def _generate_coherent_summary(cls, study_text, context_text):
        """Generate a section-by-section summary that covers the entire document."""
        try:
            if context_text:
                prompt = _SUMMARY_WITH_CONTEXT.format(
                    study_text=study_text[:cls.MAX_STUDY_CHARS],
                    context_text=context_text[:cls.MAX_CONTEXT_CHARS],
                )
            else:
                prompt = _SUMMARY_NO_CONTEXT.format(
                    study_text=study_text[:cls.MAX_STUDY_CHARS],
                )

            response = cls._model.generate_content(prompt)

            if response.text:
                summary = response.text.strip()
                if len(summary.split()) < 30:
                    # Fallback: first 10 meaningful sentences
                    sentences = [s.strip() for s in study_text.split(".") if len(s.strip()) > 25]
                    summary = ". ".join(sentences[:10]) + "."
                return summary

            return "Unable to generate summary at this time."

        except Exception as e:
            return f"Summary generation issue: {str(e)}"

    @classmethod
    def _generate_meaningful_questions(cls, study_text, context_text):
        """Generate exam-style Q&A pairs covering the entire document."""
        try:
            num_q = cls.NUM_QUESTIONS

            if context_text:
                prompt = _QA_WITH_CONTEXT.format(
                    num_questions=num_q,
                    study_text=study_text[:cls.MAX_STUDY_CHARS],
                    context_text=context_text[:cls.MAX_CONTEXT_CHARS],
                )
            else:
                prompt = _QA_NO_CONTEXT.format(
                    num_questions=num_q,
                    study_text=study_text[:cls.MAX_STUDY_CHARS],
                )

            response = cls._model.generate_content(prompt)

            if response.text:
                qa_pairs = cls._parse_qa_response(response.text)
                return {
                    "total_questions": len(qa_pairs),
                    "context_used": bool(context_text),
                    "qa_pairs": qa_pairs,
                }

            return {
                "total_questions": 0,
                "context_used": bool(context_text),
                "qa_pairs": [],
                "message": "Unable to generate questions at this time.",
            }

        except Exception as e:
            return {
                "error": f"Q&A generation failed: {str(e)}",
                "total_questions": 0,
                "context_used": False,
                "qa_pairs": [],
            }

    @classmethod
    def _parse_qa_response(cls, response_text):
        """Parse Gemini Q&A output into structured pairs."""
        qa_pairs = []
        lines = response_text.split("\n")

        current_question = None
        current_answer = []

        for line in lines:
            line = line.strip()
            if line.startswith(("Q", "Question")) and ":" in line:
                if current_question and current_answer:
                    qa_pairs.append(cls._make_qa(len(qa_pairs) + 1, current_question, current_answer))
                current_question = line.split(":", 1)[1].strip()
                current_answer = []
            elif line.startswith(("A", "Answer")) and ":" in line:
                current_answer.append(line.split(":", 1)[1].strip())
            elif current_question and line and not line.startswith(("Q", "Question", "A", "Answer")):
                current_answer.append(line)

        if current_question and current_answer:
            qa_pairs.append(cls._make_qa(len(qa_pairs) + 1, current_question, current_answer))

        if not qa_pairs:
            qa_pairs = cls._generate_fallback_questions(response_text)

        return qa_pairs[:40]

    @classmethod
    def _make_qa(cls, idx, question, answer_lines):
        return {
            "id": idx,
            "question": question,
            "answer": " ".join(answer_lines).strip(),
            "type": "concept_based",
            "difficulty": "medium",
        }

    @classmethod
    def _generate_fallback_questions(cls, text):
        sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 30]
        qa_pairs = []
        for i, sentence in enumerate(sentences[:5]):
            words = sentence.split()
            if len(words) >= 8:
                concept = " ".join(words[4:8])
                qa_pairs.append(cls._make_qa(i + 1, f"Explain the concept of {concept}?", [sentence]))
        return qa_pairs

    @classmethod
    def _parse_flashcards_response(cls, response_text):
        """Parse Gemini flashcard output into structured pairs."""
        flashcards = []
        lines = response_text.split("\n")
        current_term = None
        current_definition = []

        for line in lines:
            line = line.strip()
            if line.upper().startswith("TERM:"):
                if current_term and current_definition:
                    flashcards.append({"term": current_term, "definition": " ".join(current_definition).strip()})
                current_term = line.split(":", 1)[1].strip()
                current_definition = []
            elif line.upper().startswith("DEFINITION:"):
                current_definition.append(line.split(":", 1)[1].strip())
            elif current_term and line:
                current_definition.append(line)

        if current_term and current_definition:
            flashcards.append({"term": current_term, "definition": " ".join(current_definition).strip()})

        return flashcards