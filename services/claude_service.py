"""
Claude API wrapper – used by the agent for both analysis and generation calls.
"""
from __future__ import annotations

from typing import Any

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import settings
from utils.logger import log


class ClaudeService:
    """Thin wrapper around the Anthropic Python SDK."""

    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.claude_model

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        reraise=True,
    )
    def complete(
        self,
        system: str,
        user: str,
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> str:
        """Simple text completion – returns the assistant's text."""
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        reraise=True,
    )
    def run_agent_loop(
        self,
        system: str,
        initial_message: str,
        tools: list[dict[str, Any]],
        tool_executor: Any,  # callable(tool_name, tool_input) -> str
        max_iterations: int = 20,
    ) -> str:
        """
        Standard agentic tool-use loop.

        Args:
            system:          System prompt.
            initial_message: First user message.
            tools:           List of tool definitions (Anthropic format).
            tool_executor:   Callable that executes a tool by name and returns result string.
            max_iterations:  Safety cap on number of LLM calls.

        Returns:
            Final text response from the assistant.
        """
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": initial_message}
        ]

        for iteration in range(max_iterations):
            log.debug(f"Agent loop iteration {iteration + 1}/{max_iterations}")

            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=system,
                tools=tools,
                messages=messages,
            )

            # Append assistant response to history
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                # Extract final text
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return ""

            if response.stop_reason == "tool_use":
                tool_results: list[dict[str, Any]] = []
                for block in response.content:
                    if block.type == "tool_use":
                        log.info(f"[step]Tool call:[/step] {block.name}")
                        try:
                            result = tool_executor(block.name, block.input)
                        except Exception as exc:
                            result = f"ERROR: {exc}"
                            log.warning(f"Tool {block.name} failed: {exc}")
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": str(result),
                            }
                        )
                messages.append({"role": "user", "content": tool_results})
                continue

            # Unexpected stop reason
            log.warning(f"Unexpected stop_reason: {response.stop_reason}")
            break

        raise RuntimeError(
            f"Agent loop exceeded {max_iterations} iterations without completing."
        )
