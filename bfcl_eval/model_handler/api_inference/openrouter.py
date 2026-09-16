"""
openrouter.py

Thin subclass of OpenAICompletionsHandler for models routed through
OpenRouter (OPENAI_BASE_URL=https://openrouter.ai/api/v1, see .env).
Reuses the base class entirely -- OpenRouter itself applies each model's
correct native chat template and tool-calling format server-side, so no
per-model handler code is needed the way local-inference (vLLM) models
require.

The one thing this subclass adds: OpenRouter exposes a non-standard
`reasoning` field to control "thinking" models. Confirmed directly
(2026-09-16, a live test call) that several models default to reasoning
ON even when not asked for -- e.g. qwen/qwen3.8-27b burned 51 hidden
reasoning tokens on a two-word reply until explicitly told
`"reasoning": {"enabled": false}`. Per the project's decided policy (run
every model in direct/non-reasoning mode, since BFCL/MLCL's own
methodology assumes single-shot direct answers, and a model that reasons
past the required output format risks an unparseable answer -- observed
firsthand with Sarvam-M), this is injected into every OpenRouter call
here rather than left to each model's own default. Models without a
reasoning mode simply ignore the field.
"""

from bfcl_eval.model_handler.api_inference.openai_completion import OpenAICompletionsHandler
from overrides import override


class OpenRouterHandler(OpenAICompletionsHandler):
    @override
    def generate_with_backoff(self, **kwargs):
        kwargs.setdefault("extra_body", {})
        kwargs["extra_body"].setdefault("reasoning", {"enabled": False})
        return super().generate_with_backoff(**kwargs)
