import json

from backend.ai.prompts import SYSTEM_PROMPT
from backend.ai.provider import GroqProvider
from backend.ai.tools import TOOL_DEFINITIONS, execute_tool


MAX_TOOL_ROUNDS = 5


class InventoryAssistant:
    def __init__(self, engine):
        self.engine = engine
        self.provider = None

    def chat(
        self,
        *,
        business_id: int,
        message: str,
    ) -> str:
        message = message.strip()

        if not message:
            raise ValueError("Message is required")

        if len(message) > 2000:
            raise ValueError("Message is too long")

        if self.provider is None:
            self.provider = GroqProvider()
            
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": message,
            },
        ]

        for _ in range(MAX_TOOL_ROUNDS):
            assistant_message = self.provider.create_completion(
                messages,
                TOOL_DEFINITIONS,
            )

            tool_calls = assistant_message.tool_calls or []

            if not tool_calls:
                if not assistant_message.content:
                    raise RuntimeError(
                        "AI assistant returned an empty response"
                    )

                return assistant_message.content.strip()

            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        }
                        for call in tool_calls
                    ],
                }
            )

            for call in tool_calls:
                try:
                    arguments = json.loads(
                        call.function.arguments or "{}"
                    )
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        "AI returned invalid tool arguments"
                    ) from exc

                if not isinstance(arguments, dict):
                    raise RuntimeError(
                        "AI returned invalid tool arguments"
                    )

                result = execute_tool(
                    call.function.name,
                    arguments,
                    engine=self.engine,
                    business_id=business_id,
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.function.name,
                        "content": json.dumps(result),
                    }
                )

        raise RuntimeError(
            "AI assistant exceeded the maximum tool-call rounds"
        )