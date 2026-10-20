import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def session(headers=None):
    s = requests.Session()
    retry = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": "jobscan-research/0.1", **(headers or {})})
    return s
