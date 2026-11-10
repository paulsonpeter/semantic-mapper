"""Aircraft fault term generation through the OpenAI Responses API."""
import json
import os
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from aircraft_normalizer import MAX_CHARACTERS, SYSTEM_PROMPT

MODEL = "gpt-4.1-mini"


def normalize_report(paragraph, model=MODEL, api_key=None):
    if not isinstance(paragraph, str) or not paragraph.strip():
        raise ValueError("Enter a maintenance or fault report paragraph.")
    if len(paragraph) > MAX_CHARACTERS:
        raise ValueError(f"Use at most {MAX_CHARACTERS:,} characters.")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("Configure OPENAI_MODEL in Streamlit Secrets.")
    api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("The cloud model is not configured yet. Add OPENAI_API_KEY in this app's Streamlit Secrets.")
    payload = {
        "model": model.strip(), "store": False,
        "instructions": SYSTEM_PROMPT, "input": paragraph.strip(),
        "max_output_tokens": 200,
        "text": {"format": {
            "type": "json_schema", "name": "aircraft_fault_term", "strict": True,
            "schema": {"type": "object", "properties": {"normalized_term": {"type": "string"}},
                       "required": ["normalized_term"], "additionalProperties": False},
        }},
    }
    request = Request("https://api.openai.com/v1/responses",
                      data=json.dumps(payload).encode("utf-8"),
                      headers={"Authorization": "Bearer " + api_key.strip(),
                               "Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=60) as response:
            body = json.load(response)
        if body.get("status") != "completed":
            raise ValueError("The cloud model did not complete its response. Try again.")
        parts = [part for item in body.get("output", []) if item.get("type") == "message"
                 for part in item.get("content", [])]
        if any(part.get("type") == "refusal" for part in parts):
            raise ValueError("The cloud model could not normalize this report. Try rephrasing it.")
        text = "".join(part["text"] for part in parts if part.get("type") == "output_text")
        result = json.loads(text)
        term = result["normalized_term"]
        if not isinstance(term, str):
            raise TypeError("Invalid term")
        term = " ".join(term.upper().split())
        if not re.fullmatch(r"[A-Z0-9]+(?: [A-Z0-9]+){1,4}", term):
            raise ValueError("The cloud model did not return a short fault term. Try again.")
        return {"normalized_term": term}
    except HTTPError as exc:
        messages = {
            401: "OpenAI rejected the API key. Update OPENAI_API_KEY in Streamlit Secrets.",
            403: "OpenAI denied access. Check API key permissions and model access.",
            404: "OpenAI model not available. Check OPENAI_MODEL in Streamlit Secrets.",
            429: "OpenAI usage or rate limit reached. Check API billing and limits, then try again.",
        }
        raise ValueError(messages.get(exc.code, "The cloud model request failed. Please try again.")) from None
    except (OSError, TimeoutError):
        raise ValueError("Cannot reach OpenAI right now. Please try again.") from None
    except (KeyError, TypeError, AttributeError, json.JSONDecodeError):
        raise ValueError("The cloud model returned an invalid result. Please try again.") from None
