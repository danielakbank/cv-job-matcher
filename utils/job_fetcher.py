import requests
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Adzuna config ──
ADZUNA_APP_ID   = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY  = os.getenv("ADZUNA_APP_KEY")
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"

# ── Reed config ──
REED_API_KEY    = os.getenv("REED_API_KEY")
REED_BASE_URL   = "https://www.reed.co.uk/api/1.0/search"

# ── Remotive config (no key needed) ──
REMOTIVE_BASE_URL = "https://remotive.com/api/remote-jobs"

DEFAULT_COUNTRY          = "gb"
DEFAULT_RESULTS_PER_PAGE = 10
REQUEST_TIMEOUT          = 10


# ─────────────────────────────────────────────
# ADZUNA
# ─────────────────────────────────────────────

def _fetch_adzuna_jobs(keywords: str, country: str, results_per_page: int) -> list[dict]:
    """
    Fetch job listings from Adzuna API.

    Args:
        keywords: Search keywords
        country: Country code (e.g. 'gb', 'us')
        results_per_page: Number of results to return

    Returns:
        List of normalised job dictionaries
    """
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        logger.warning("Adzuna credentials missing — skipping Adzuna search.")
        return []

    url    = f"{ADZUNA_BASE_URL}/{country}/search/1"
    params = {
        "app_id":           ADZUNA_APP_ID,
        "app_key":          ADZUNA_APP_KEY,
        "results_per_page": results_per_page,
        "what":             keywords,
        "content-type":     "application/json",
    }

    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        jobs = response.json().get("results", [])
        logger.info(f"Adzuna returned {len(jobs)} jobs for '{keywords}'")
        return [_normalise_adzuna_job(job) for job in jobs]
    except requests.exceptions.Timeout:
        logger.warning("Adzuna request timed out.")
        return []
    except requests.exceptions.RequestException as e:
        logger.warning(f"Adzuna request failed: {e}")
        return []


def _normalise_adzuna_job(job: dict) -> dict:
    """Normalise an Adzuna job listing into the standard format."""
    return {
        "title":       job.get("title", "No title provided"),
        "company":     job.get("company", {}).get("display_name", "Unknown company"),
        "location":    job.get("location", {}).get("display_name", "Unknown location"),
        "description": job.get("description", "No description available"),
        "salary_min":  job.get("salary_min"),
        "salary_max":  job.get("salary_max"),
        "url":         job.get("redirect_url", "#"),
        "created":     job.get("created", "")[:10],
        "source":      "Adzuna",
    }


# ─────────────────────────────────────────────
# REED
# ─────────────────────────────────────────────

def _fetch_reed_jobs(keywords: str, results_per_page: int) -> list[dict]:
    """
    Fetch job listings from Reed API (UK only).

    Args:
        keywords: Search keywords
        results_per_page: Number of results to return

    Returns:
        List of normalised job dictionaries
    """
    if not REED_API_KEY:
        logger.warning("Reed API key missing — skipping Reed search.")
        return []

    params = {
        "keywords":        keywords,
        "resultsToTake":   results_per_page,
        "resultsToSkip":   0,
    }

    try:
        response = requests.get(
            REED_BASE_URL,
            params=params,
            auth=(REED_API_KEY, ""),
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        jobs = response.json().get("results", [])
        logger.info(f"Reed returned {len(jobs)} jobs for '{keywords}'")
        return [_normalise_reed_job(job) for job in jobs]
    except requests.exceptions.Timeout:
        logger.warning("Reed request timed out.")
        return []
    except requests.exceptions.RequestException as e:
        logger.warning(f"Reed request failed: {e}")
        return []


def _normalise_reed_job(job: dict) -> dict:
    """Normalise a Reed job listing into the standard format."""
    return {
        "title":       job.get("jobTitle", "No title provided"),
        "company":     job.get("employerName", "Unknown company"),
        "location":    job.get("locationName", "Unknown location"),
        "description": job.get("jobDescription", "No description available"),
        "salary_min":  job.get("minimumSalary"),
        "salary_max":  job.get("maximumSalary"),
        "url":         job.get("jobUrl", "#"),
        "created":     str(job.get("date", ""))[:10],
        "source":      "Reed",
    }


# ─────────────────────────────────────────────
# REMOTIVE (no API key needed — remote jobs)
# ─────────────────────────────────────────────

def _fetch_remotive_jobs(keywords: str, results_per_page: int) -> list[dict]:
    """
    Fetch remote job listings from Remotive API (no key required).

    Args:
        keywords: Search keywords
        results_per_page: Number of results to return

    Returns:
        List of normalised job dictionaries
    """
    params = {"search": keywords, "limit": results_per_page}

    try:
        response = requests.get(REMOTIVE_BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        jobs = response.json().get("jobs", [])
        logger.info(f"Remotive returned {len(jobs)} jobs for '{keywords}'")
        return [_normalise_remotive_job(job) for job in jobs]
    except requests.exceptions.Timeout:
        logger.warning("Remotive request timed out.")
        return []
    except requests.exceptions.RequestException as e:
        logger.warning(f"Remotive request failed: {e}")
        return []


def _normalise_remotive_job(job: dict) -> dict:
    """Normalise a Remotive job listing into the standard format."""
    return {
        "title":       job.get("title", "No title provided"),
        "company":     job.get("company_name", "Unknown company"),
        "location":    job.get("candidate_required_location", "Remote"),
        "description": job.get("description", "No description available"),
        "salary_min":  None,
        "salary_max":  None,
        "url":         job.get("url", "#"),
        "created":     job.get("publication_date", "")[:10],
        "source":      "Remotive",
    }


# ─────────────────────────────────────────────
# DEDUPLICATION
# ─────────────────────────────────────────────

def _deduplicate_jobs(jobs: list[dict]) -> list[dict]:
    """
    Remove duplicate job listings based on title and company name.

    Args:
        jobs: Combined list of jobs from all sources

    Returns:
        Deduplicated list of jobs
    """
    seen    = set()
    unique  = []

    for job in jobs:
        key = (
            job.get("title", "").lower().strip(),
            job.get("company", "").lower().strip(),
        )
        if key not in seen:
            seen.add(key)
            unique.append(job)

    logger.info(f"Deduplication: {len(jobs)} → {len(unique)} jobs")
    return unique


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

def fetch_jobs(
    keywords: str,
    country: str = DEFAULT_COUNTRY,
    results_per_page: int = DEFAULT_RESULTS_PER_PAGE,
    include_remote: bool = True,
) -> list[dict]:
    """
    Fetch job listings from all available sources (Adzuna, Reed, Remotive)
    and return a combined, deduplicated list.

    Sources are searched in parallel-style — if one fails it is skipped
    gracefully and the others still return results.

    Args:
        keywords: Search terms (e.g. job title from CV suggestions)
        country: Country code for Adzuna/Reed (default: 'gb')
        results_per_page: Results to fetch per source (default: 10)
        include_remote: Whether to include Remotive remote jobs (default: True)

    Returns:
        Combined, deduplicated list of normalised job dictionaries

    Raises:
        RuntimeError: If all sources return no results
    """
    if not keywords or not keywords.strip():
        raise ValueError("Keywords cannot be empty.")

    logger.info(f"Fetching jobs from all sources — keywords: '{keywords}'")

    all_jobs = []

    # Fetch from each source — failures are handled inside each function
    all_jobs.extend(_fetch_adzuna_jobs(keywords, country, results_per_page))
    all_jobs.extend(_fetch_reed_jobs(keywords, results_per_page))

    if include_remote:
        all_jobs.extend(_fetch_remotive_jobs(keywords, results_per_page))

    if not all_jobs:
        logger.warning("All job sources returned no results.")
        return []

    deduplicated = _deduplicate_jobs(all_jobs)
    logger.info(f"Total jobs after deduplication: {len(deduplicated)}")

    return deduplicated