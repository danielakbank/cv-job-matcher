import json
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
GROQ_API_KEY        = os.getenv("GROQ_API_KEY")
CV_TRUNCATION_LIMIT = 4000
MAX_TOKENS          = 2000
TEMPERATURE         = 0.6

# Primary model with ordered fallbacks
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
    Build a structured prompt that instructs the LLM to return
    role suggestions as a strict JSON object.

    Args:
        cv_text: Extracted CV text, truncated to token-safe length

    Returns:
        Formatted prompt string
    """
    truncated_cv = cv_text[:CV_TRUNCATION_LIMIT]

    return f"""
You are an expert career advisor and recruitment specialist.

Carefully analyse the CV below. Consider:
- All work experience and job titles
- Technical and soft skills (stated and implied)
- Education and qualifications
- Projects and achievements
- Transferable skills the candidate may not realise they have

Return ONLY a valid JSON object — no preamble, no explanation, no markdown fences.

The JSON must follow this exact structure:
{{
  "strengths_summary": "3-4 sentences summarising what makes this candidate unique. Reference specific things from their CV.",
  "roles": [
    {{
      "title": "Job Title",
      "category": "Obvious Match",
      "reason": "2 sentences explaining why this candidate fits this role.",
      "salary": "£30,000 – £45,000"
    }}
  ]
}}

Rules:
- "category" must be exactly one of: "Obvious Match", "Stretch Role", "Hidden Gem"
- Include 4-5 Obvious Matches, 3-4 Stretch Roles, 3-4 Hidden Gems
- "Obvious Match" = roles they are fully qualified for right now
- "Stretch Role" = roles within reach with minor upskilling
- "Hidden Gem" = surprising roles their transferable skills suit well
- Salary must be a realistic UK range in £
- Do not invent skills or experience not present in the CV
- Return ONLY the JSON. No other text whatsoever.

**CV:**
{truncated_cv}
""".strip()


def _call_groq_with_fallback(client: Groq, prompt: str) -> str:
    """
    Attempt Groq API call with automatic model fallback.

    Tries each model in MODELS order. If a model is decommissioned
    or unavailable, moves to the next automatically.

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
                            "You return only valid JSON — no preamble, "
                            "no explanation, no markdown. Pure JSON only."
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


def suggest_job_roles(cv_text: str) -> tuple[list[dict], str]:
    """
    Analyse a CV and return structured role suggestions using Groq LLM.

    Returns roles across three tiers:
    - Obvious Matches: roles the candidate is fully qualified for
    - Stretch Roles: roles requiring minor upskilling
    - Hidden Gems: surprising roles based on transferable skills

    Automatically falls back to alternative models if the primary fails.

    Args:
        cv_text: Extracted text from the user's CV

    Returns:
        Tuple of (list of role dicts, strengths summary string)
        Each role dict has keys: title, category, reason, salary

    Raises:
        EnvironmentError: If Groq API key is missing
        ValueError: If CV text is empty or JSON cannot be parsed
        RuntimeError: If all model attempts fail
    """
    if not cv_text or not cv_text.strip():
        raise ValueError("CV text is empty. Cannot generate job suggestions.")

    _validate_credentials()

    client = _build_client()
    prompt = _build_suggestion_prompt(cv_text)

    logger.info("Sending CV to Groq for job role suggestions...")

    raw = _call_groq_with_fallback(client, prompt)

    # Strip accidental markdown fences if model adds them
    clean = (
        raw.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )

    try:
        data = json.loads(clean)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed: {e}\nRaw response:\n{raw}")
        raise ValueError(
            "Role suggestions were returned in an unexpected format. "
            "Please try uploading your CV again."
        ) from e

    roles   = data.get("roles", [])
    summary = data.get("strengths_summary", "")

    if not roles:
        raise ValueError(
            "No roles were returned in the analysis. "
            "Please try uploading your CV again."
        )

    logger.info(f"Successfully parsed {len(roles)} roles from Groq response.")
    return roles, summary