"""HTTPS client for the Payments CI publisher."""

import json
import os
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPOSITORY = "https://github.com/MichalBoczula/ECommerceStorePayments"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PactRegistry:
    def __init__(self):
        registry = urlsplit(os.environ.get("PACT_REGISTRY_URL", ""))
        self.token = os.environ.get("PACT_PUBLISHER_TOKEN", "")
        if (
            registry.scheme != "https"
            or not registry.hostname
            or registry.username is not None
            or registry.password is not None
            or registry.path not in ("", "/")
            or registry.query
            or registry.fragment
            or not self.token
        ):
            raise ValueError("Configure an HTTPS PACT_REGISTRY_URL origin and the Payments PACT_PUBLISHER_TOKEN.")
        self.origin = f"https://{registry.netloc}"
        self.opener = build_opener(NoRedirect())

    def call(self, path, body=None, *, raw=False):
        headers = (
            {}
            if body is None
            else {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            }
        )
        req = Request(self.origin + path, data=None if body is None else json.dumps(body).encode(), headers=headers)
        try:
            with self.opener.open(req, timeout=30) as response:
                return response.read() if raw else json.load(response)
        except HTTPError as error:
            raise RuntimeError(f"Pact registry rejected {path} with HTTP {error.code}.") from None
