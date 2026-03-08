import google.generativeai as genai
from .gemini_config import GeminiConfig

# ── Prompt templates ────────────────────────────────────────────────────────

_SUMMARY_WITH_CONTEXT = """
You are a university lecturer creating a comprehensive study summary for students.

Your task is to summarize the ENTIRE document below. Do NOT skip any section.
Work through the material from start to finish.

RULES:
- Cover EVERY topic, heading, and concept — nothing is optional
- Use the exact terminology from the document (students are tested on specific terms)
- Include all definitions, lists, classifications, and named techniques
- Preserve numbered lists exactly as they appear (e.g. "3 benefits of X", "4 types of Y")
- Flag every named concept, term, framework, method, or tool introduced in the document
- Format with headings that match the document's own section headings

OUTPUT FORMAT:
Use markdown with ## headings for major sections, ### for sub-sections.
End with a "Key Terms to Know" section listing every named concept.

STUDY MATERIAL:
{study_text}

PAST QUESTIONS (use these to understand what the examiner focuses on):
{context_text}

Write the complete summary now:
"""

_SUMMARY_NO_CONTEXT = """
You are a university lecturer creating a comprehensive study summary for students.

Your task is to summarize the ENTIRE document below. Do NOT skip any section.
Work through the material from start to finish.

RULES:
- Cover EVERY topic, heading, and concept — nothing is optional
- Use the exact terminology from the document (students are tested on specific terms)
- Include all definitions, lists, classifications, and named techniques
- Preserve numbered lists exactly as they appear (e.g. "3 benefits of X", "4 types of Y")
- Flag every named concept, term, framework, method, or tool introduced in the document
- Format with headings that match the document's own section headings

OUTPUT FORMAT:
Use markdown with ## headings for major sections, ### for sub-sections.
End with a "Key Terms to Know" section listing every named concept.

STUDY MATERIAL:
{study_text}

Write the complete summary now:
"""

_QA_WITH_CONTEXT = """
You are a university exam setter.

Generate {num_questions} exam-style questions. Model your style EXACTLY after the past questions provided.

QUESTION STYLE RULES:
- Use imperative verbs: "State", "List", "Define", "Explain", "Describe", "What is", "How does"
- Be SPECIFIC and DIRECT — not vague (e.g. "State 3 benefits of X" not "Discuss X")
- Include counts when the material gives them ("State 4 challenges...", "List 5 sources...")
- Mix types: definitions (25%), lists (30%), explanations (30%), comparisons (15%)
- Spread questions across the ENTIRE document — do not cluster on one topic
- Answers must use exact terms from the material

PAST QUESTIONS (mirror this style):
{context_text}

STUDY MATERIAL:
{study_text}

OUTPUT FORMAT:

Q1: [Question]
A1: [Answer]

Q2: [Question]
A2: [Answer]

...continue for all {num_questions} questions.
"""

_QA_NO_CONTEXT = """
You are a university exam setter.

Generate {num_questions} exam-style questions from the study material.

QUESTION STYLE RULES:
- Use imperative verbs: "State", "List", "Define", "Explain", "Describe", "What is", "How does"
- Be SPECIFIC and DIRECT — not vague (e.g. "State 3 benefits of X" not "Discuss X")
- Include counts when the material gives them ("State 4 challenges...", "List 5 sources...")
- Mix types: definitions (25%), lists (30%), explanations (30%), comparisons (15%)
- Spread questions across the ENTIRE document — do not cluster on one topic
- Answers must use exact terms from the material

STUDY MATERIAL:
{study_text}

OUTPUT FORMAT:

Q1: [Question]
A1: [Answer]

Q2: [Question]
A2: [Answer]

...continue for all {num_questions} questions.
"""


# ── Processor ────────────────────────────────────────────────────────────────

class AIProcessor:
    """
    AI processor using Google Gemini with improved limits and prompt quality.
    Generates comprehensive, exam-aligned summaries and questions.
    """

    _model = None
    _models_loaded = False

    # ── Config ────────────────────────────────────────────────────────────

    NUM_QUESTIONS = 15       # questions per document (free tier)
    MAX_STUDY_CHARS = 50_000
    MAX_CONTEXT_CHARS = 10_000

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

    # ── Private helpers ───────────────────────────────────────────────────

    @classmethod
    def _preprocess_study_text(cls, text):
        """Select up to 30 good paragraphs (free tier limit)."""
        if not text:
            return ""

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        good = [p for p in paragraphs if len(p) >= 100 and len(p.split()) >= 15]
        selected = good[:30]

        if not selected:
            return text[:50_000]

        return "\n\n".join(selected)

    @classmethod
    def _generate_coherent_summary(cls, study_text, context_text):
        """Generate a section-by-section summary."""
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
                    sentences = [s.strip() for s in study_text.split(".") if len(s.strip()) > 25]
                    summary = ". ".join(sentences[:4]) + "."
                return summary

            return "Unable to generate summary at this time."

        except Exception as e:
            return f"Summary generation issue: {str(e)}"

    @classmethod
    def _generate_meaningful_questions(cls, study_text, context_text):
        """Generate exam-style Q&A pairs."""
        try:
            num_q = cls.NUM_QUESTIONS

            if context_text:
                prompt = _QA_WITH_CONTEXT.format(
                    num_questions=num_q,
                    study_text=study_text[:40_000],
                    context_text=context_text[:cls.MAX_CONTEXT_CHARS],
                )
            else:
                prompt = _QA_NO_CONTEXT.format(
                    num_questions=num_q,
                    study_text=study_text[:40_000],
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

        return qa_pairs[:15]

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
    def _extract_key_concepts(cls, text):
        sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 40]
        concepts = []
        for sentence in sentences[:8]:
            words = sentence.split()
            if len(words) >= 5:
                concept = " ".join(words[3:8])
                concepts.append((concept, sentence))
        return concepts[:5]