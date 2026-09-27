"""Check authentication and print only status and quota, never credentials."""
import json
from datetime import datetime, timezone
import requests

from study_config import ROOT, load_openalex_key, openalex_headers


def main():
    key_present = bool(load_openalex_key())
    result = {"checked_utc": datetime.now(timezone.utc).isoformat(), "key_present": key_present}
    if not key_present:
        result["status"] = "key_missing"
    else:
        response = requests.get("https://api.openalex.org/rate-limit", headers=openalex_headers(), timeout=45)
        result["http_status"] = response.status_code
        result["status"] = "authenticated" if response.ok else "authentication_or_access_failed"
        result["quota_headers"] = {k: v for k, v in response.headers.items()
                                   if k.lower().startswith("x-ratelimit-") or k.lower() == "retry-after"}
        if response.ok:
            payload = response.json()
            # Rate-limit values only; omit any identity/account/token fields.
            def quota_only(obj):
                if not isinstance(obj, dict):
                    return {}
                return {k: quota_only(v) if isinstance(v, dict) else v
                        for k, v in obj.items()
                        if not any(s in k.lower() for s in ("key", "token", "email", "user", "account", "name", "id"))
                        and (isinstance(v, (dict, int, float, bool)) or any(s in k.lower() for s in ("reset", "limit", "remaining", "credit", "cost", "budget")))}
            result["quota"] = quota_only(payload)
    (ROOT / "data/openalex_authenticated_access.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
