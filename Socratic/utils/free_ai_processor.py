import google.generativeai as genai
from .gemini_config import GeminiConfig

# ── Prompt templates ────────────────────────────────────────────────────────

_SUMMARY_WITH_CONTEXT = """
You are a friendly university tutor explaining study material to a student in plain, simple English.

Your task is to write a COMPLETE study guide covering EVERY section of the notes below.
The student should be able to read your guide and actually understand the material — not just memorise copied definitions.

WRITING RULES (follow every single one):
- Write as if explaining to a smart friend who has never studied this topic before.
- After every technical term, add a plain-English explanation in parentheses.
  Example: "Elasticity (think of it like a rubber band — you can stretch your computing resources up during busy periods and shrink them back down when things are quiet)"
- NEVER copy a sentence word-for-word from the notes. Always rephrase in your own words.
- For every numbered list in the notes, keep the numbers AND explain what each item means in simple terms.
- Use real-world analogies and everyday examples wherever possible.
- Cover EVERY heading and sub-heading from the notes without skipping any.
- The past exam questions are provided to help you understand which topics the examiner considers most important — give those topics extra depth and clarity.

OUTPUT FORMAT — use exactly this markdown structure for each section:

## [Section heading that matches the notes]

[2-3 sentence plain-English overview of what this section is about and why it matters]

### Key Concepts
- **[Term]**: [Plain-English explanation in 1-3 sentences. Include an analogy if it helps.]
- **[Term]**: [Plain-English explanation in 1-3 sentences. Include an analogy if it helps.]

### Why This Matters
[1-2 sentences on how this topic is used in the real world or why it appears in exams]

---

Repeat this block for EVERY section in the notes. Do not skip any section.

After all sections, add:

## Quick Reference: Key Terms
| Term | What it actually means |
|------|------------------------|
| [term] | [one plain-English sentence] |

---

STUDY NOTES (cover every section):
{study_text}

PAST EXAM QUESTIONS (use these to identify which topics need the most depth):
{context_text}

Write the complete study guide now, starting with the first section:
"""

_SUMMARY_NO_CONTEXT = """
You are a friendly university tutor explaining study material to a student in plain, simple English.

Your task is to write a COMPLETE study guide covering EVERY section of the notes below.
The student should be able to read your guide and actually understand the material — not just memorise copied definitions.

WRITING RULES (follow every single one):
- Write as if explaining to a smart friend who has never studied this topic before.
- After every technical term, add a plain-English explanation in parentheses.
  Example: "Multitenancy (imagine an apartment building — multiple tenants share the same building infrastructure but each has their own private space)"
- NEVER copy a sentence word-for-word from the notes. Always rephrase in your own words.
- For every numbered list in the notes, keep the numbers AND explain what each item means in simple terms.
- Use real-world analogies and everyday examples wherever possible.
- Cover EVERY heading and sub-heading from the notes without skipping any.

OUTPUT FORMAT — use exactly this markdown structure for each section:

## [Section heading that matches the notes]

[2-3 sentence plain-English overview of what this section is about and why it matters]

### Key Concepts
- **[Term]**: [Plain-English explanation in 1-3 sentences. Include an analogy if it helps.]
- **[Term]**: [Plain-English explanation in 1-3 sentences. Include an analogy if it helps.]

### Why This Matters
[1-2 sentences on how this topic is used in the real world or why it appears in exams]

---

Repeat this block for EVERY section in the notes. Do not skip any section.

After all sections, add:

## Quick Reference: Key Terms
| Term | What it actually means |
|------|------------------------|
| [term] | [one plain-English sentence] |

---

STUDY NOTES (cover every section):
{study_text}

Write the complete study guide now, starting with the first section:
"""

_QA_WITH_CONTEXT = """
You are a university exam setter creating practice questions for a student.

CRITICAL FORMAT RULES — the output will be parsed by code so you MUST follow these exactly:
- Every question line starts with EXACTLY: Q<number>: (e.g. Q1: Q2: Q15:)
- Every answer line starts with EXACTLY: A<number>: (e.g. A1: A2: A15:)
- The number on Q and A must always match.
- Put ONE blank line between each Q/A pair.
- Write NOTHING before Q1 — no titles, no preamble, no instructions, no introductions.
- Do NOT use Q or A prefixes inside answer text itself.

QUESTION QUALITY RULES:
- Use action verbs: "Explain", "Define", "State", "List", "Describe", "Compare", "What is", "Why is", "How does"
- Be specific: write "State 3 advantages of cloud computing" not "Discuss cloud computing"
- When the notes mention a specific count (e.g. "5 types of X"), ask the student to name all of them.
- Spread questions evenly across ALL sections — do not ask more than 2 questions on the same topic.
- Model your question style closely after the past exam questions provided.

ANSWER QUALITY RULES:
- Write answers in plain, clear English that a student can actually learn from.
- After technical terms, briefly clarify what they mean.
- Answers should be 2-5 sentences — detailed enough to be useful, short enough to study from.
- Do NOT copy sentences word-for-word from the notes.
- Do NOT start answers with "According to the notes" or similar phrases.

PAST EXAM QUESTIONS (model your style and difficulty level on these):
{context_text}

Generate exactly {num_questions} questions covering the full breadth of the notes.

STUDY NOTES:
{study_text}

Start immediately with Q1 (absolutely nothing before it):
"""

_QA_NO_CONTEXT = """
You are a university exam setter creating practice questions for a student.

CRITICAL FORMAT RULES — the output will be parsed by code so you MUST follow these exactly:
- Every question line starts with EXACTLY: Q<number>: (e.g. Q1: Q2: Q15:)
- Every answer line starts with EXACTLY: A<number>: (e.g. A1: A2: A15:)
- The number on Q and A must always match.
- Put ONE blank line between each Q/A pair.
- Write NOTHING before Q1 — no titles, no preamble, no instructions, no introductions.
- Do NOT use Q or A prefixes inside answer text itself.

QUESTION QUALITY RULES:
- Use action verbs: "Explain", "Define", "State", "List", "Describe", "Compare", "What is", "Why is", "How does"
- Be specific: write "State 3 advantages of cloud computing" not "Discuss cloud computing"
- When the notes mention a specific count (e.g. "5 types of X"), ask the student to name all of them.
- Spread questions evenly across ALL sections — do not ask more than 2 questions on the same topic.

ANSWER QUALITY RULES:
- Write answers in plain, clear English that a student can actually learn from.
- After technical terms, briefly clarify what they mean.
- Answers should be 2-5 sentences — detailed enough to be useful, short enough to study from.
- Do NOT copy sentences word-for-word from the notes.
- Do NOT start answers with "According to the notes" or similar phrases.

Generate exactly {num_questions} questions. Start with foundational definitions, move to
processes and mechanisms, then finish with applications and comparisons.

STUDY NOTES:
{study_text}

Start immediately with Q1 (absolutely nothing before it):
"""

_FLASHCARD = """
You are creating study flashcards for a university student preparing for an exam.

Each flashcard must be MEMORABLE and genuinely UNDERSTANDABLE — not a copied dictionary definition.

RULES FOR EVERY CARD:
- The TERM should be a single important concept, acronym, or technique from the notes.
- The DEFINITION must:
  * Be written in plain, conversational English (no copying from the notes)
  * Be 1-3 sentences maximum
  * Include a real-world analogy or everyday example where it helps understanding
  * Explain WHY it matters or how it is used, not just what it is
- BANNED phrases — never write these:
  * "A concept related to..."
  * "An important technique used in..."
  * "This refers to..."
  * "A term that describes..."
  * Any other vague filler opener

GOOD EXAMPLE:
TERM: Elasticity
DEFINITION: The ability to automatically scale your computing resources up or down based on demand — like a hotel that can add or remove rooms depending on how many guests are booked. This means you only pay for what you actually use and never run out of capacity during busy periods.

BAD EXAMPLE:
TERM: Elasticity
DEFINITION: A cloud computing attribute that refers to the ability to increase or decrease resources as needed.

STRICT FORMAT — use exactly this pattern, nothing else before or between cards:

TERM: [term or acronym]
DEFINITION: [plain-English explanation with example]

TERM: [term or acronym]
DEFINITION: [plain-English explanation with example]

Generate exactly {num_cards} flashcards covering the most important and exam-likely terms.

STUDY NOTES:
{study_text}

Start immediately with the first TERM (nothing before it):
"""


# ── Processor ────────────────────────────────────────────────────────────────

import re

class AIProcessor:
    """
    Free-tier AI processor using Google Gemini.
    15 questions, processes up to 30 good paragraphs.
    """

    _model = None
    _models_loaded = False

    # ── Config ────────────────────────────────────────────────────────────

    NUM_QUESTIONS  = 15
    NUM_FLASHCARDS = 20
    MAX_STUDY_CHARS   = 50_000
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
                    "The document doesn't contain enough readable text to process. "
                    "Please make sure your file has actual content and try again.",
                    {"total_questions": 0, "qa_pairs": [], "context_used": False},
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
        good = [p for p in paragraphs if len(p) >= 80 and len(p.split()) >= 12]
        selected = good[:30]

        if not selected:
            return text[:cls.MAX_STUDY_CHARS]

        return "\n\n".join(selected)

    @classmethod
    def _generate_coherent_summary(cls, study_text, context_text):
        """Generate a plain-English, section-by-section summary."""
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
                    # Fallback: first few meaningful sentences
                    sentences = [s.strip() for s in study_text.split(".") if len(s.strip()) > 25]
                    summary = ". ".join(sentences[:4]) + "."
                return summary

            return "Unable to generate summary at this time."

        except Exception as e:
            return f"Summary generation issue: {str(e)}"

    @classmethod
    def _generate_meaningful_questions(cls, study_text, context_text):
        """Generate exam-style Q&A pairs with a robust parser."""
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
                    "context_used":    bool(context_text),
                    "qa_pairs":        qa_pairs,
                }

            return {
                "total_questions": 0,
                "context_used":    bool(context_text),
                "qa_pairs":        [],
                "message":         "Unable to generate questions at this time.",
            }

        except Exception as e:
            return {
                "error":           f"Q&A generation failed: {str(e)}",
                "total_questions": 0,
                "context_used":    False,
                "qa_pairs":        [],
            }

    @classmethod
    def _parse_qa_response(cls, response_text):
        """
        Robust regex-based parser.
        Matches lines that start with Q<number>: or A<number>:
        Ignores any prose that happens to start with Q or A (e.g. prompt echoes).
        """
        # Strip bold/italic markers some models add  (**Q1:** → Q1:)
        text = re.sub(r"\*+", "", response_text)

        question_re = re.compile(
            r"^Q(\d+)\s*[:\.\)]\s*(.+?)(?=^Q\d+\s*[:\.\)]|^A\d+\s*[:\.\)]|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        answer_re = re.compile(
            r"^A(\d+)\s*[:\.\)]\s*(.+?)(?=^Q\d+\s*[:\.\)]|^A\d+\s*[:\.\)]|\Z)",
            re.MULTILINE | re.DOTALL,
        )

        questions = {int(m.group(1)): m.group(2).strip() for m in question_re.finditer(text)}
        answers   = {int(m.group(1)): m.group(2).strip() for m in answer_re.finditer(text)}

        pairs = []
        for idx in sorted(questions):
            if idx in answers:
                pairs.append({
                    "id":         idx,
                    "question":   questions[idx],
                    "answer":     answers[idx],
                    "type":       "concept_based",
                    "difficulty": "medium",
                })

        if not pairs:
            pairs = cls._generate_fallback_questions(response_text)

        return pairs[:cls.NUM_QUESTIONS]

    @classmethod
    def _make_qa(cls, idx, question, answer_lines):
        return {
            "id":         idx,
            "question":   question,
            "answer":     " ".join(answer_lines).strip(),
            "type":       "concept_based",
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