import os

from groq import APIError, Groq

DEFAULT_MODEL = "openai/gpt-oss-20b"


class GroqProvider:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not configured")

        model = os.getenv("GROQ_MODEL", DEFAULT_MODEL)

        self.client = Groq(api_key=api_key)
        self.model = model

    def create_completion(self, messages, tools=None):
        request = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }

        if tools:
            request["tools"] = tools
            request["tool_choice"] = "auto"

        try:
            response = self.client.chat.completions.create(**request)
        
        except APIError as exc:
            raise RuntimeError("Groq request failed") from exc

        if not response.choices:
            raise RuntimeError("Groq returned no response")

        return response.choices[0].message