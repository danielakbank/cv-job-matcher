import logging
import os
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
GROQ_API_KEY             = os.getenv("GROQ_API_KEY")
CV_TRUNCATION_LIMIT      = 4000
MAX_TOKENS               = 2000
TEMPERATURE              = 0.6

# Primary model with ordered fallbacks — if one is decommissioned, next is tried
MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]


def _validate_credentials() -> None:
    """
    Ensure Groq API key is present before making any requests.

    Raises:
        EnvironmentError: If the API key is missing
    """
    if not GROQ_API_KEY:
        raise EnvironmentError(
            "Groq API key is missing. "
            "Ensure GROQ_API_KEY is set in your .env file."
        )


def _build_client() -> Groq:
    """
    Initialise and return an authenticated Groq client.

    Returns:
        Groq client instance
    """
    return Groq(api_key=GROQ_API_KEY)


def _build_suggestion_prompt(cv_text: str) -> str:
    """
    Build a structured prompt instructing the LLM to analyse the CV
    and return role suggestions across three tiers.

    Args:
        cv_text: Extracted CV text (will be truncated to token-safe length)

    Returns:
        Formatted prompt string
    """
    truncated_cv = cv_text[:CV_TRUNCATION_LIMIT]

    return f"""
You are an expert career advisor and recruitment specialist with deep knowledge
of the job market across all industries.

Carefully read the CV below and analyse:
- All work experience and job titles
- Technical and soft skills (both stated and implied)
- Education and qualifications
- Projects and achievements
- Industries worked in
- Transferable skills the candidate may not realise they have

Then suggest job roles in THREE categories.

Use EXACTLY this format for every role so it can be parsed correctly:

---

**OBVIOUS ROLES** — Roles they are clearly qualified for right now:

**[Job Title]**
Why they fit: [2 sentences explaining the fit]
Salary: [Typical UK salary range e.g. £35,000 – £50,000]

**[Job Title]**
Why they fit: [2 sentences]
Salary: [range]

(List 4–5 roles in this section)

---

**STRETCH ROLES** — Roles they could move into with minor upskilling:

**[Job Title]**
Why they fit: [2 sentences]
To bridge the gap: [1 sentence on what they need to add]
Salary: [range]

(List 3–4 roles in this section)

---

**HIDDEN ROLES** — Surprising roles they probably haven't considered:

**[Job Title]**
Why they fit: [2 sentences explaining transferable fit]
What excites employers: [1 sentence]
Salary: [range]

(List 3–4 roles in this section)

---

**KEY STRENGTHS SUMMARY**
[3–4 sentences summarising what makes this candidate unique. Reference specific things from their CV.]

---

Be specific and honest. Do not invent experience. Base everything strictly on the CV below.

**CV:**
{truncated_cv}
""".strip()


def _call_groq_with_fallback(client: Groq, prompt: str) -> str:
    """
    Attempt to call Groq using the primary model, falling back to
    alternatives if the model is unavailable or decommissioned.

    Args:
        client: Authenticated Groq client
        prompt: Formatted prompt string

    Returns:
        Raw response text from the model

    Raises:
        RuntimeError: If all models fail
    """
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
                            "You are an expert career advisor. "
                            "Provide specific, honest, and genuinely useful career guidance. "
                            "Identify transferable skills and hidden opportunities. "
                            "Always follow the exact formatting structure requested."
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


def suggest_job_roles(cv_text: str) -> str:
    """
    Analyse a CV and suggest suitable job roles using Groq LLM.

    Produces three tiers of suggestions:
    - Obvious roles the candidate is already qualified for
    - Stretch roles requiring minor upskilling
    - Hidden roles based on transferable skills they may not have considered

    Automatically falls back to alternative models if the primary is unavailable.

    Args:
        cv_text: Extracted text from the user's CV

    Returns:
        Formatted string containing job role suggestions and analysis

    Raises:
        EnvironmentError: If Groq API key is missing
        ValueError: If CV text is empty
        RuntimeError: If all model attempts fail
    """
    if not cv_text or not cv_text.strip():
        raise ValueError("CV text is empty. Cannot generate job suggestions.")

    _validate_credentials()

    client = _build_client()
    prompt = _build_suggestion_prompt(cv_text)

    logger.info("Sending CV to Groq for job role suggestions...")

    suggestions = _call_groq_with_fallback(client, prompt)

    logger.info("Job role suggestions received successfully.")
    return suggestions