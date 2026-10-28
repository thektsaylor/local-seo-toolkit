"""Small DataForSEO API client. Standard library only.

Credentials come from DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD, either already
set in the environment or read from a .env file in the repo root. They are the
API login and password from the DataForSEO dashboard, not your account email.
"""
import base64
import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://api.dataforseo.com"
REPO_ROOT = Path(__file__).resolve().parent.parent

# 40101 is a temporary Google-side error that almost always clears on a retry.
RETRY_STATUS = {40101}


class DataForSEOError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(f"{code}: {message}")
        self.code = code


def load_env(path=REPO_ROOT / ".env"):
    """Read KEY=value lines from .env without overriding real environment variables."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class DataForSEO:
    def __init__(self, login=None, password=None, timeout=120):
        load_env()
        login = login or os.environ.get("DATAFORSEO_LOGIN")
        password = password or os.environ.get("DATAFORSEO_PASSWORD")
        if not login or not password:
            raise SystemExit(
                "Missing DataForSEO credentials. Copy .env.example to .env and fill in "
                "DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD from your DataForSEO dashboard.")
        token = base64.b64encode(f"{login}:{password}".encode()).decode()
        self._headers = {"Authorization": "Basic " + token, "Content-Type": "application/json"}
        self._timeout = timeout
        self._lock = threading.Lock()
        self.spent = 0.0  # running total of what this session's calls cost, in USD

    def _request(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(BASE_URL + path, data=data, method=method, headers=self._headers)
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.load(resp)

    def balance(self):
        """Current prepaid balance in USD. This call is free."""
        payload = self._request("GET", "/v3/appendix/user_data")
        return float(payload["tasks"][0]["result"][0]["money"]["balance"])

    def live(self, path, task, attempts=3):
        """Post one task to a live endpoint and return its first result object."""
        for attempt in range(attempts):
            last_try = attempt == attempts - 1
            try:
                payload = self._request("POST", path, [task])
            except urllib.error.HTTPError as err:
                if err.code >= 500 and not last_try:
                    time.sleep(2 ** attempt)
                    continue
                raise
            result_task = payload["tasks"][0]
            with self._lock:
                self.spent += float(result_task.get("cost") or 0)
            code = result_task["status_code"]
            if code == 20000:
                return (result_task.get("result") or [{}])[0] or {}
            if code in RETRY_STATUS and not last_try:
                time.sleep(2 ** attempt)
                continue
            raise DataForSEOError(code, result_task.get("status_message"))
