import requests
import logging
import os
import streamlit as st
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Adzuna ──
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID") or st.secrets.get("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY") or st.secrets.get("ADZUNA_APP_KEY")
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"

# ── Reed ──
REED_API_KEY = os.getenv("REED_API_KEY") or st.secrets.get("REED_API_KEY")
REED_BASE_URL = "https://www.reed.co.uk/api/1.0/search"

# ── Remotive (no key needed) ──
REMOTIVE_BASE_URL = "https://remotive.com/api/remote-jobs"

# ── postcodes.io (free, no key needed) ──
POSTCODES_IO_URL = "https://api.postcodes.io/postcodes"

# ── ip-api (free, no key needed) ──
IPAPI_URL = "http://ip-api.com/json"

DEFAULT_COUNTRY          = "gb"
DEFAULT_RESULTS_PER_PAGE = 10
DEFAULT_RADIUS_KM        = 30
REQUEST_TIMEOUT          = 10


# ─────────────────────────────────────────────
# LOCATION DATA CLASS
# ─────────────────────────────────────────────

@dataclass
class LocationFilter:
    """
    Holds a resolved location used to geographically filter job results.

    Attributes:
        postcode:   Raw postcode entered by the user (e.g. "M1 1AE")
        display:    Human-readable label for the UI (e.g. "Manchester, M1 1AE")
        latitude:   Resolved latitude coordinate
        longitude:  Resolved longitude coordinate
        radius_km:  Search radius in kilometres (default: 30)
        source:     How the location was obtained — "postcode" | "ip" | "none"
    """
    postcode:  Optional[str]   = None
    display:   str             = ""
    latitude:  Optional[float] = None
    longitude: Optional[float] = None
    radius_km: int             = DEFAULT_RADIUS_KM
    source:    str             = "none"


# ─────────────────────────────────────────────
# GEOLOCATION HELPERS
# ─────────────────────────────────────────────

def geocode_postcode(postcode: str) -> Optional[LocationFilter]:
    """
    Resolve a UK postcode to lat/lng using the free postcodes.io API.

    Args:
        postcode: UK postcode string (e.g. "M1 1AE" or "M11AE")

    Returns:
        Populated LocationFilter on success, None on failure.
    """
    clean = postcode.strip().upper().replace(" ", "")
    if not clean:
        return None

    url = f"{POSTCODES_IO_URL}/{clean}"
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 404:
            logger.warning(f"Postcode not found: {postcode!r}")
            return None
        response.raise_for_status()
        result = response.json().get("result", {})
        if not result:
            return None

        district = result.get("admin_district", "")
        label    = f"{district}, {postcode.strip().upper()}" if district else postcode.strip().upper()

        return LocationFilter(
            postcode  = postcode.strip().upper(),
            display   = label,
            latitude  = result["latitude"],
            longitude = result["longitude"],
            source    = "postcode",
        )
    except requests.exceptions.Timeout:
        logger.warning("postcodes.io request timed out.")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Postcode geocoding failed: {e}")
        return None


def detect_location_from_ip() -> Optional[LocationFilter]:
    """
    Detect approximate location from the server's public IP via ip-api.com.
    This is a best-effort fallback — accuracy varies by ISP.

    Returns:
        Populated LocationFilter on success, None on failure.
    """
    try:
        response = requests.get(IPAPI_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "success":
            logger.warning(f"ip-api non-success: {data.get('message')}")
            return None

        city = data.get("city", "")
        country = data.get("country", "")
        lat  = data.get("lat")
        lon  = data.get("lon")

        if lat is None or lon is None:
            return None

        display = ", ".join(filter(None, [city, country]))

        return LocationFilter(
            postcode  = None,
            display   = display,
            latitude  = lat,
            longitude = lon,
            source    = "ip",
        )
    except requests.exceptions.Timeout:
        logger.warning("ip-api request timed out.")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"IP geolocation failed: {e}")
        return None


# ─────────────────────────────────────────────
# ADZUNA
# ─────────────────────────────────────────────

def _fetch_adzuna_jobs(
    keywords: str,
    country: str,
    results_per_page: int,
    location: Optional[LocationFilter] = None,
) -> list[dict]:
    """
    Fetch jobs from Adzuna, optionally filtered by postcode and radius.

    Adzuna supports:
      - 'where'    : postcode or city name string
      - 'distance' : radius in km from the 'where' location

    Args:
        keywords:         Search keywords
        country:          Adzuna country code (e.g. 'gb', 'us')
        results_per_page: Number of results to fetch
        location:         Optional LocationFilter for geographic filtering

    Returns:
        List of normalised job dicts
    """
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        logger.warning("Adzuna credentials missing — skipping.")
        return []

    url    = f"{ADZUNA_BASE_URL}/{country}/search/1"
    params: dict = {
        "app_id":           ADZUNA_APP_ID,
        "app_key":          ADZUNA_APP_KEY,
        "results_per_page": results_per_page,
        "what":             keywords,
        "content-type":     "application/json",
        "sort_by":          "relevance",
    }

    if location and location.source != "none":
        where = location.postcode or location.display
        if where:
            params["where"]    = where
            params["distance"] = location.radius_km
            logger.info(f"Adzuna: where={where!r}, distance={location.radius_km}km")

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

def _fetch_reed_jobs(
    keywords: str,
    results_per_page: int,
    location: Optional[LocationFilter] = None,
) -> list[dict]:
    """
    Fetch jobs from Reed (UK only), optionally filtered by postcode and radius.

    Reed supports:
      - 'locationName'         : postcode or city name string
      - 'distanceFromLocation' : radius in MILES (we convert from km)

    Args:
        keywords:         Search keywords
        results_per_page: Number of results to fetch
        location:         Optional LocationFilter for geographic filtering

    Returns:
        List of normalised job dicts
    """
    if not REED_API_KEY:
        logger.warning("Reed API key missing — skipping.")
        return []

    params: dict = {
        "keywords":      keywords,
        "resultsToTake": results_per_page,
        "resultsToSkip": 0,
    }

    if location and location.source != "none":
        where = location.postcode or location.display
        if where:
            radius_miles = max(1, round(location.radius_km * 0.621371))
            params["locationName"]         = where
            params["distanceFromLocation"] = radius_miles
            logger.info(f"Reed: locationName={where!r}, distance={radius_miles} miles")

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
# REMOTIVE  (remote only — location not applied)
# ─────────────────────────────────────────────

def _fetch_remotive_jobs(keywords: str, results_per_page: int) -> list[dict]:
    """
    Fetch remote jobs from Remotive (no API key required).
    Location filtering is intentionally not applied — remote jobs are global.

    Args:
        keywords:         Search keywords
        results_per_page: Number of results to fetch

    Returns:
        List of normalised job dicts
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
    Remove duplicate listings based on (title, company) key pair.

    Args:
        jobs: Combined list from all sources

    Returns:
        Deduplicated list preserving original order
    """
    seen:   set[tuple[str, str]] = set()
    unique: list[dict]           = []

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
    country: str                       = DEFAULT_COUNTRY,
    results_per_page: int              = DEFAULT_RESULTS_PER_PAGE,
    include_remote: bool               = True,
    location: Optional[LocationFilter] = None,
) -> list[dict]:
    """
    Fetch job listings from all available sources, optionally filtered by
    postcode or geolocation, then deduplicate and return the combined list.

    Location filtering behaviour per source:
      - Adzuna  : 'where' + 'distance' params applied when location provided
      - Reed    : 'locationName' + 'distanceFromLocation' applied (UK only)
      - Remotive: location NOT applied — remote jobs are always global

    Args:
        keywords:         Search terms (e.g. a job title)
        country:          Adzuna country code (default: 'gb')
        results_per_page: Results per source (default: 10)
        include_remote:   Include Remotive remote jobs (default: True)
        location:         Optional LocationFilter. Build one with:
                            geocode_postcode("M1 1AE")
                            detect_location_from_ip()

    Returns:
        Combined, deduplicated list of normalised job dicts.
        Each dict has keys: title, company, location, description,
        salary_min, salary_max, url, created, source.

    Raises:
        ValueError: If keywords are empty
    """
    if not keywords or not keywords.strip():
        raise ValueError("Keywords cannot be empty.")

    loc_label = location.display if location else "none"
    logger.info(
        f"Fetching jobs — keywords: {keywords!r}, "
        f"country: {country!r}, location: {loc_label!r}"
    )

    all_jobs: list[dict] = []

    all_jobs.extend(_fetch_adzuna_jobs(keywords, country, results_per_page, location))
    all_jobs.extend(_fetch_reed_jobs(keywords, results_per_page, location))

    if include_remote:
        all_jobs.extend(_fetch_remotive_jobs(keywords, results_per_page))

    if not all_jobs:
        logger.warning("All job sources returned no results.")
        return []

    deduplicated = _deduplicate_jobs(all_jobs)
    logger.info(f"Total after deduplication: {len(deduplicated)}")
    return deduplicated