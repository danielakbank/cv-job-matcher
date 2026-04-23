import logging
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import streamlit as st

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_NAME             = "all-MiniLM-L6-v2"
SCORE_MULTIPLIER       = 100
MIN_DESCRIPTION_LENGTH = 20


# ── Define FIRST, then call ──

@st.cache_resource
def load_model() -> SentenceTransformer:
    """
    Load and cache the SentenceTransformer model.
    st.cache_resource ensures it loads once and is reused across
    all sessions — critical for fast cold starts on Streamlit Cloud.
    """
    logger.info(f"Loading sentence transformer model: {MODEL_NAME}")
    return SentenceTransformer(MODEL_NAME)


# Now safe to call
try:
    model = load_model()
    logger.info("Model loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load SentenceTransformer model: {e}")
    raise RuntimeError(
        f"Could not load the NLP model '{MODEL_NAME}'. "
        "Ensure sentence-transformers is installed correctly."
    ) from e


def _validate_inputs(cv_text: str, jobs: list[dict]) -> None:
    if not cv_text or not cv_text.strip():
        raise ValueError("CV text is empty. Please upload a valid CV.")
    if not jobs:
        raise ValueError("No job listings provided to score against.")


def _get_job_description(job: dict) -> str:
    title       = job.get("title", "")
    company     = job.get("company", "")
    description = job.get("description", "")
    combined    = f"{title} {company} {description}".strip()
    if len(combined) < MIN_DESCRIPTION_LENGTH:
        logger.warning(f"Job '{title}' has very little text — score may be unreliable.")
    return combined


def _compute_similarity(cv_embedding: np.ndarray, job_embedding: np.ndarray) -> float:
    similarity = cosine_similarity([cv_embedding], [job_embedding])[0][0]
    return round(float(similarity) * SCORE_MULTIPLIER, 2)


def score_jobs(cv_text: str, jobs: list[dict]) -> list[dict]:
    _validate_inputs(cv_text, jobs)
    logger.info(f"Scoring {len(jobs)} jobs against CV...")

    try:
        cv_embedding      = model.encode(cv_text, show_progress_bar=False)
        job_descriptions  = [_get_job_description(job) for job in jobs]
        job_embeddings    = model.encode(job_descriptions, show_progress_bar=False, batch_size=32)
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise RuntimeError("Failed to generate embeddings. Please try again.") from e

    scored_jobs = []
    for job, job_embedding in zip(jobs, job_embeddings):
        try:
            score = _compute_similarity(cv_embedding, job_embedding)
            scored_jobs.append({**job, "match_score": score})
            logger.info(f"Scored '{job.get('title', 'Unknown')}' — {score}%")
        except Exception as e:
            logger.warning(f"Could not score '{job.get('title', 'Unknown')}': {e}")
            continue

    scored_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    logger.info(f"Scoring complete — {len(scored_jobs)} jobs scored.")
    return scored_jobs