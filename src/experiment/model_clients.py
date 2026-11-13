"""Model clients for GUSSET experiment.

Supports Anthropic, OpenAI, and NVIDIA (OpenAI-compatible) chat APIs.
Reads API keys from environment variables.
Each client is a callable(model_name, prompt) -> str matching the runner's model_interface.

NVIDIA client matches the working format:
  base_url = "https://integrate.api.nvidia.com/v1"
  model = "nvidia/nemotron-3.5-super-vl-120b-a12b"
  stream=True with reasoning_content collection
  extra_body={"chat_template_kwargs": {"enable_thinking": True}}
"""

import os
from abc import ABC, abstractmethod


class ModelClient(ABC):
    @abstractmethod
    def __call__(self, model_name: str, prompt: str) -> str:
        ...


class AnthropicClient(ModelClient):
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("Install anthropic: pip install anthropic")

    def __call__(self, model_name: str, prompt: str) -> str:
        resp = self._client.messages.create(
            model=model_name,
            max_tokens=500,
            temperature=0.0,
            system="You are a careful decision advisor. Answer exactly in the requested format.",
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text


class OpenAIClient(ModelClient):
    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        try:
            import openai
            self._client = openai.OpenAI(api_key=self.api_key, base_url=base_url)
        except ImportError:
            raise ImportError("Install openai: pip install openai")

    def __call__(self, model_name: str, prompt: str) -> str:
        resp = self._client.chat.completions.create(
            model=model_name,
            temperature=0.0,
            messages=[{"role": "system", "content": "You are a careful decision advisor. Answer exactly in the requested format."},
                      {"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content


class NVIDIAClient(ModelClient):
    """NVIDIA NIMs API — OpenAI-compatible endpoint.

    Matches the working format with streaming, reasoning content, and extra_body.
    """

    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY")
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY not set")
        self.base_url = base_url or "https://integrate.api.nvidia.com/v1"
        try:
            import openai
            self._client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=float(os.environ.get("NVIDIA_TIMEOUT", "240")),
            )
        except ImportError:
            raise ImportError("Install openai: pip install openai")

    def __call__(self, model_name: str, prompt: str) -> str:
        """Stream the response and collect reasoning_content + content."""
        # Defaults match the known-working request. Environment overrides make
        # pilot runs faster without changing the registered default.
        #
        # The decision contract is a structured recomputation, not an open
        # deliberation. It uses a non-thinking call with a small token budget
        # so the final two lines are not truncated. The initial, defended, and
        # final phases keep thinking enabled.
        is_contract = "DECISION CONTRACT" in prompt
        thinking = os.environ.get("NVIDIA_THINKING", "1") not in {"0", "false", "False"}
        if is_contract:
            thinking = False
        max_tokens = int(os.environ.get("NVIDIA_CONTRACT_MAX_TOKENS", "1024")) if is_contract else int(
            os.environ.get("NVIDIA_MAX_TOKENS", "16384")
        )
        resp = self._client.chat.completions.create(
            model=model_name,
            temperature=float(os.environ.get("NVIDIA_TEMPERATURE", "1")),
            top_p=0.95,
            max_tokens=max_tokens,
            seed=int(os.environ.get("NVIDIA_SEED", "42")),
            parallel_tool_calls=True,
            stream=True,
            extra_body={"chat_template_kwargs": {"enable_thinking": thinking}},
            messages=[{"role": "system", "content": "You are a careful decision advisor. Answer exactly in the requested format."},
                      {"role": "user", "content": prompt}],
        )

        full_content = ""
        full_reasoning = ""
        for chunk in resp:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                full_reasoning += reasoning
            if delta.content is not None:
                full_content += delta.content

        # Return content with reasoning prepended if present
        if full_reasoning:
            return f"[REASONING]\n{full_reasoning}\n[/REASONING]\n\n{full_content}"
        return full_content


def make_client(provider: str, **kwargs) -> ModelClient:
    providers = {
        "anthropic": AnthropicClient,
        "openai": OpenAIClient,
        "nvidia": NVIDIAClient,
    }
    if provider not in providers:
        raise ValueError(f"Unknown provider: {provider}. Choose from {list(providers)}")
    return providers[provider](**kwargs)


if __name__ == "__main__":
    print("Model clients module loaded.")
    print("Available providers: anthropic, openai, nvidia")
    print("Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or NVIDIA_API_KEY to run live trials.")
    print("NVIDIA client uses streaming + reasoning_content + extra_body format.")