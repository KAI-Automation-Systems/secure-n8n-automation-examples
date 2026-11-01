"""Offline by default; explicitly opted-in, fixed-host Anthropic adapter."""
import json
import os
import urllib.request

from .core import canonical, strict_json


class OfflineProvider:
    def classify(self, features):
        return {"category": "technical" if features["technical"] else
                "billing" if features["billing"] else "general",
                "priority": "high" if features["urgent"] else "normal"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class AnthropicProvider:
    def __init__(self):
        if os.environ.get("ALLOW_EXTERNAL_MODEL") != "true":
            raise ValueError("External processing must be explicitly enabled")
        self.key = os.environ["ANTHROPIC_API_KEY"]
        self.model = os.environ["ANTHROPIC_MODEL"]
        # Ignore proxy environment variables; never permit user supplied URLs or
        # redirects that could forward API credentials to a different origin.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def classify(self, features):
        if set(features) != {"billing", "technical", "urgent"} or not all(type(v) is bool for v in features.values()):
            raise ValueError("Feature-only egress required")
        payload = {"model": self.model, "max_tokens": 96,
                   "system": 'Return JSON only with category (billing, technical, general) and priority (normal, high). technical takes precedence over billing; urgent means high. No other fields.',
                   "messages": [{"role": "user", "content": canonical(features)}]}
        request = urllib.request.Request("https://api.anthropic.com/v1/messages",
                    data=canonical(payload).encode(), method="POST",
                    headers={"Content-Type": "application/json", "x-api-key": self.key,
                             "anthropic-version": "2023-06-01"})
        with self.opener.open(request, timeout=8) as response:
            raw = response.read(32769)
        if len(raw) > 32768:
            raise ValueError("Response too large")
        result = strict_json(raw)
        if result.get("stop_reason") != "end_turn":
            raise ValueError("Incomplete model response")
        blocks = result.get("content", [])
        if len(blocks) != 1 or blocks[0].get("type") != "text":
            raise ValueError("Unexpected content")
        return strict_json(blocks[0]["text"].encode())
