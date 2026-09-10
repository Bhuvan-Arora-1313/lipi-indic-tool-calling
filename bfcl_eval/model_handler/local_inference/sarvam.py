import re
from typing import Any

from bfcl_eval.model_handler.local_inference.base_oss_handler import OSSHandler
from overrides import override


class SarvamHandler(OSSHandler):
    """
    Sarvam-M/30B/105B, run in BFCL's standard "prompting" style (is_fc_model=
    False), not native function-calling.

    History: a first attempt (SarvamFCHandler, since removed) assumed
    Sarvam-M would honor Mistral-style [AVAILABLE_TOOLS]/[TOOL_CALLS]
    special tokens, since its tokenizer inherited them from its Mistral-
    Small base. A real pipeline-check run on the cluster (2026-09-10)
    showed this was wrong: Sarvam-M ignored that prompt structure entirely
    and just reasoned in prose, occasionally referencing a function
    Python-call-style inside an explanation (e.g. "you could use
    `triangle_properties.get({...})`") rather than emitting a parseable
    tagged response. 0% accuracy, confirmed by inspecting raw output before
    trusting the number.

    This handler instead relies on BFCL's standard, well-tested prompting
    pipeline: the default system prompt (built by
    system_prompt_pre_processing_chat_model, NOT overridden here) already
    explicitly instructs "respond with a python list of function calls in
    the format [func1(a=1,b=2), func2(c=3)]". Sarvam's own real chat
    template ([SYSTEM_PROMPT]...[/SYSTEM_PROMPT], [INST]...[/INST] --
    verified against its actual tokenizer_config.json, not assumed) is used
    to render that. Since Sarvam-M still tends to add surrounding prose /
    markdown even when told not to (observed above), decode_ast/decode_execute
    first try to isolate a fenced code block or a bracketed call-list
    substring before handing off to the default AST-based parser, rather
    than assuming the whole response is bare call syntax.

    Whether this actually works needs the same treatment as the first
    attempt: verify with a small pipeline-check run before trusting a full
    result, not assumed correct just because it compiles.
    """

    def __init__(
        self,
        model_name,
        temperature,
        registry_name,
        is_fc_model,
        dtype="bfloat16",
        **kwargs,
    ) -> None:
        super().__init__(model_name, temperature, registry_name, is_fc_model, **kwargs)

    @staticmethod
    def _isolate_call_list(result: str) -> str:
        """Best-effort extraction of the actual function-call-list substring
        out of a response that may contain surrounding prose/explanation."""
        text = result.strip()

        # Prefer the last fenced code block, if any -- Sarvam-M tends to put
        # the actual call there even while explaining around it.
        fence_matches = re.findall(r"```(?:python|json)?\s*(.*?)```", text, re.DOTALL)
        if fence_matches:
            text = fence_matches[-1].strip()

        # Otherwise (or still), look for the last top-level [...] or a bare
        # call-list-shaped run of `name(...)[, name(...)]*`.
        bracket_matches = re.findall(r"\[.*?\]", text, re.DOTALL)
        if bracket_matches:
            return bracket_matches[-1]

        call_matches = re.findall(r"[A-Za-z_][A-Za-z0-9_.]*\([^()]*\)", text, re.DOTALL)
        if call_matches:
            return ", ".join(call_matches)

        return text

    @override
    def decode_ast(self, result, language, has_tool_call_tag):
        cleaned = self._isolate_call_list(result)
        return super().decode_ast(cleaned, language, has_tool_call_tag)

    @override
    def decode_execute(self, result, has_tool_call_tag):
        cleaned = self._isolate_call_list(result)
        return super().decode_execute(cleaned, has_tool_call_tag)

    @override
    def _parse_query_response_prompting(self, api_response: Any) -> dict:
        model_response = api_response.choices[0].text

        reasoning_content = ""
        cleaned_response = model_response
        if "<think>" in model_response and "</think>" in model_response:
            parts = model_response.split("</think>")
            reasoning_content = parts[0].rstrip("\n").split("<think>")[-1].lstrip("\n")
            cleaned_response = parts[-1].lstrip("\n")

        return {
            "model_responses": cleaned_response,
            "reasoning_content": reasoning_content,
            "input_token": api_response.usage.prompt_tokens,
            "output_token": api_response.usage.completion_tokens,
        }

    @override
    def _add_assistant_message_prompting(
        self, inference_data: dict, model_response_data: dict
    ) -> dict:
        inference_data["message"].append(
            {
                "role": "assistant",
                "content": model_response_data["model_responses"],
            }
        )
        return inference_data

    @override
    def _format_prompt(self, messages, function):
        # Sarvam-M's real chat template (verified against its actual
        # tokenizer_config.json on HuggingFace, 2026-09-10): system message
        # wrapped in [SYSTEM_PROMPT]...[/SYSTEM_PROMPT] (not embedded in the
        # first [INST], unlike vanilla Mistral), user/assistant turns as
        # plain [INST]...[/INST]. No native tool-call handling in the
        # template at all -- the function docs arrive pre-baked into the
        # system message text by the default prompting pipeline, so nothing
        # tool-specific needs to happen at this layer.
        bos_token = "<s>"
        eos_token = "</s>"

        first_message = messages[0]
        if first_message["role"] == "system":
            system_message = first_message["content"]
            loop_messages = messages[1:]
        else:
            system_message = "You are a helpful assistant."
            loop_messages = messages

        formatted_prompt = bos_token + f"[SYSTEM_PROMPT]{system_message}[/SYSTEM_PROMPT]"

        for message in loop_messages:
            role = message["role"]
            content = message["content"]
            if role == "user":
                formatted_prompt += f"[INST]{content}[/INST]"
            elif role == "assistant":
                formatted_prompt += f"{content}{eos_token}"

        return formatted_prompt
