import logging
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MODEL_NAME = "all-MiniLM-L6-v2"
SCORE_MULTIPLIER = 100
MIN_DESCRIPTION_LENGTH = 20


# Load model once at module level — avoids reloading on every function call
try:
    logger.info(f"Loading sentence transformer model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    logger.info("Model loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load SentenceTransformer model: {e}")
    raise RuntimeError(
        f"Could not load the NLP model '{MODEL_NAME}'. "
        "Ensure sentence-transformers is installed correctly."
    ) from e


def _validate_inputs(cv_text: str, jobs: list[dict]) -> None:
    """
    Validate that CV text and job listings are usable before scoring.

    Args:
        cv_text: Extracted text from the user's CV
        jobs: List of job dictionaries from Adzuna

    Raises:
        ValueError: If inputs are empty or invalid
    """
    if not cv_text or not cv_text.strip():
        raise ValueError("CV text is empty. Please upload a valid CV.")

    if not jobs:
        raise ValueError("No job listings provided to score against.")


def _get_job_description(job: dict) -> str:
    """
    Build a combined text representation of a job for embedding.
    Combines title, company, and description for richer comparison.

    Args:
        job: A job dictionary from job_fetcher

    Returns:
        Combined string of job fields
    """
    title = job.get("title", "")
    company = job.get("company", "")
    description = job.get("description", "")

    combined = f"{title} {company} {description}".strip()

    if len(combined) < MIN_DESCRIPTION_LENGTH:
        logger.warning(f"Job '{title}' has very little text — score may be unreliable.")

    return combined


def _compute_similarity(cv_embedding: np.ndarray, job_embedding: np.ndarray) -> float:
    """
    Compute cosine similarity between CV and job embeddings.

    Args:
        cv_embedding: Embedding vector for the CV
        job_embedding: Embedding vector for a job listing

    Returns:
        Similarity score as a percentage (0.0 to 100.0), rounded to 2 decimal places
    """
    similarity = cosine_similarity([cv_embedding], [job_embedding])[0][0]
    return round(float(similarity) * SCORE_MULTIPLIER, 2)


def score_jobs(cv_text: str, jobs: list[dict]) -> list[dict]:
    """
    Score each job listing against the CV using semantic similarity.

    Embeddings are generated using a SentenceTransformer model.
    Each job is assigned a match score between 0 and 100.
    Results are returned sorted by score, highest first.

    Args:
        cv_text: Extracted text from the user's CV
        jobs: List of job dictionaries from job_fetcher

    Returns:
        List of job dictionaries with an added 'match_score' field,
        sorted by match_score descending

    Raises:
        ValueError: If CV text or jobs are invalid
        RuntimeError: If embedding or scoring fails
    """
    _validate_inputs(cv_text, jobs)

    logger.info(f"Scoring {len(jobs)} jobs against CV...")

    try:
        # Generate CV embedding once — reused for all job comparisons
        cv_embedding = model.encode(cv_text, show_progress_bar=False)

        # Generate all job embeddings in a single batch — more efficient
        job_descriptions = [_get_job_description(job) for job in jobs]
        job_embeddings = model.encode(job_descriptions, show_progress_bar=False, batch_size=32)

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise RuntimeError("Failed to generate embeddings for scoring. Please try again.") from e

    scored_jobs = []

    for job, job_embedding in zip(jobs, job_embeddings):
        try:
            score = _compute_similarity(cv_embedding, job_embedding)
            scored_job = {**job, "match_score": score}
            scored_jobs.append(scored_job)
            logger.info(f"Scored '{job.get('title', 'Unknown')}' — {score}%")
        except Exception as e:
            logger.warning(f"Could not score job '{job.get('title', 'Unknown')}': {e}")
            continue

    # Sort by match score, highest first
    scored_jobs.sort(key=lambda x: x["match_score"], reverse=True)

    logger.info(f"Scoring complete. {len(scored_jobs)} jobs scored successfully.")

    return scored_jobs