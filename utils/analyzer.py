import logging
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MAX_TOKENS   = 350  # Hard ceiling — keeps responses tight
TEMPERATURE  = 0.5  # Lower = more consistent, less waffle

CV_TRUNCATION_LIMIT          = 3000
DESCRIPTION_TRUNCATION_LIMIT = 1500

MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]


def _validate_credentials() -> None:
    if not GROQ_API_KEY:
        raise EnvironmentError(
            "Groq API key is missing. Ensure GROQ_API_KEY is set in your .env file."
        )


def _build_client() -> Groq:
    return Groq(api_key=GROQ_API_KEY)


def _build_prompt(cv_text: str, job: dict) -> str:
    truncated_cv  = cv_text[:CV_TRUNCATION_LIMIT]
    truncated_desc = job.get("description", "")[:DESCRIPTION_TRUNCATION_LIMIT]

    return f"""
You are a straight-talking recruiter giving a candidate fast, honest feedback.

Analyse this CV against the job and respond in EXACTLY this format — nothing more:

VERDICT: [One sentence. Does this person fit? Be direct.]

✅ YOU HAVE:
- [Specific strength from their CV]
- [Specific strength from their CV]
- [Specific strength from their CV]

❌ YOU'RE MISSING:
- [Specific gap for this role]
- [Specific gap for this role]

💡 ONE THING TO DO:
- [Single most impactful action they can take — concrete, not generic]

Rules:
- Total response must be under 150 words
- Plain English only — no jargon, no corporate language
- Reference actual details from the CV and job description
- Do not add any extra sections, intros, or sign-offs

---

CV:
{truncated_cv}

---

Job Title: {job.get("title", "Not provided")}
Company: {job.get("company", "Not provided")}
Job Description:
{truncated_desc}
""".strip()


def _call_groq_with_fallback(client: Groq, prompt: str) -> str:
    last_error = None

    for model in MODELS:
        try:
            logger.info(f"Attempting Groq request with model: {model}")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a direct, no-nonsense recruiter. "
                            "Give short, specific, honest feedback. "
                            "Never exceed 150 words. Never add extra sections. "
                            "Follow the exact format you are given."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
            )
            logger.info(f"Groq request succeeded with model: {model}")
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.warning(f"Model '{model}' failed: {e}")
            last_error = e
            continue

    raise RuntimeError(
        f"All Groq models failed. Last error: {last_error}. "
        "Check your API key and internet connection."
    )


def analyse_match(cv_text: str, job: dict) -> str:
    if not cv_text or not cv_text.strip():
        raise ValueError("CV text is empty. Cannot perform analysis.")
    if not job:
        raise ValueError("No job provided for analysis.")

    _validate_credentials()

    client = _build_client()
    prompt = _build_prompt(cv_text, job)

    logger.info(f"Sending analysis request for: '{job.get('title', 'Unknown')}'")
    analysis = _call_groq_with_fallback(client, prompt)
    logger.info(f"Analysis received for: '{job.get('title', 'Unknown')}'")

    return analysis