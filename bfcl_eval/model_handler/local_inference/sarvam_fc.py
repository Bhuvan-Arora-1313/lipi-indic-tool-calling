import json
import random
import string
from typing import Any

from bfcl_eval.model_handler.local_inference.base_oss_handler import OSSHandler
from bfcl_eval.model_handler.utils import convert_to_function_call
from overrides import override


class SarvamFCHandler(OSSHandler):
    """
    Sarvam-M/30B/105B are Indic-native models; Sarvam-M is post-trained on a
    Mistral-Small base and its tokenizer inherited Mistral's tool-calling
    special tokens ([AVAILABLE_TOOLS], [TOOL_CALLS], [TOOL_RESULTS], [INST]).

    IMPORTANT, verified directly from the real tokenizer_config.json on
    HuggingFace (sarvamai/sarvam-m, 2026-09-10), not assumed from memory:
    the model's own shipped chat_template does NOT actually implement tool
    calling at all (no `tools` handling, no `role == "tool"` branch) --
    despite having the special tokens in vocabulary. It also wraps the
    system message in [SYSTEM_PROMPT]...[/SYSTEM_PROMPT], unlike vanilla
    Mistral's template (which embeds it inside the first [INST] block, see
    mistral_fc.py) -- so that existing handler can't just be reused as-is.

    This handler manually constructs a Mistral-style AVAILABLE_TOOLS/
    TOOL_CALLS prompt (same convention as mistral_fc.py) adapted to
    Sarvam's real [SYSTEM_PROMPT] wrapping, since the special tokens exist
    and this is the standard convention for this model family. This is a
    reasonable hypothesis given the vocabulary, NOT independently confirmed
    against Sarvam's own docs -- verify against a real small-scale run
    before trusting a full-scale result, same as any new handler.

    Also explicitly suppresses "thinking" mode (Sarvam-M defaults to a
    <think>...</think> reasoning block otherwise, confirmed via a live
    Ollama test earlier in this project -- see LOG.md) by using the
    template's own "default_nothink_system_message" text when the test
    entry has no system message, matching what passing enable_thinking=False
    to the real chat template would have done.
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

    @override
    def decode_ast(self, result, language, has_tool_call_tag):
        if type(result) != list:
            raise ValueError(f"Model did not return a list of function calls: {result}")
        return result

    @override
    def decode_execute(self, result, has_tool_call_tag):
        if type(result) != list:
            raise ValueError(f"Model did not return a list of function calls: {result}")
        return convert_to_function_call(result)

    @staticmethod
    def _construct_func_doc(functions):
        func_docs = []
        for tool in functions:
            func_doc = '{"type": "function", "function": {'
            func_doc += ", ".join(
                (
                    f'"{key}": "{val}"'
                    if isinstance(val, str)
                    else f'"{key}": {json.dumps(val)}'
                )
                for key, val in tool.items()
                if key != "return"
            )
            func_doc += "}}"
            func_docs.append(func_doc)

        return "[AVAILABLE_TOOLS][" + ", ".join(func_docs) + "][/AVAILABLE_TOOLS]"

    @override
    def _format_prompt(self, messages, function):
        bos_token = "<s>"
        eos_token = "</s>"
        default_nothink_system_message = "You are a helpful assistant."

        first_message = messages[0]
        if first_message["role"] == "system":
            system_message = first_message["content"]
            loop_messages = messages[1:]
        else:
            system_message = default_nothink_system_message
            loop_messages = messages

        formatted_prompt = bos_token + f"[SYSTEM_PROMPT]{system_message}[/SYSTEM_PROMPT]"

        user_messages = [msg for msg in loop_messages if msg["role"] == "user"]

        for message in loop_messages:
            role = message["role"]

            if role == "user":
                if len(function) > 0 and message == user_messages[-1]:
                    formatted_prompt += self._construct_func_doc(function)
                formatted_prompt += f"[INST]{message['content']}[/INST]"

            elif role == "assistant":
                formatted_prompt += f"{message['content']}{eos_token}"

            elif role == "tool":
                tool_results = {
                    "content": message["content"],
                    "call_id": message["tool_call_id"],
                }
                formatted_prompt += f"[TOOL_RESULTS]{json.dumps(tool_results)}[/TOOL_RESULTS]"

        return formatted_prompt

    @override
    def _pre_query_processing_prompting(self, test_entry: dict) -> dict:
        functions: list = test_entry["function"]
        return {"message": [], "function": functions}

    @override
    def _add_execution_results_prompting(
        self, inference_data: dict, execution_results: list[str], model_response_data: dict
    ) -> dict:
        for execution_result, tool_call_id in zip(
            execution_results, model_response_data["tool_call_ids"]
        ):
            inference_data["message"].append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": execution_result,
                }
            )
        return inference_data

    @staticmethod
    def generate_random_string() -> str:
        characters = string.ascii_letters + string.digits
        return "".join(random.choices(characters, k=9))

    @override
    def _parse_query_response_prompting(self, api_response: Any) -> dict:
        model_responses = api_response.choices[0].text
        tool_call_ids = []

        # Strip a visible <think>...</think> block if the model produced one
        # despite the nothink system message (belt and suspenders).
        cleaned = model_responses
        if "<think>" in cleaned and "</think>" in cleaned:
            cleaned = cleaned.split("</think>")[-1].lstrip("\n")

        try:
            parsed = json.loads(cleaned)
            for item in parsed:
                tool_call_id = self.generate_random_string()
                item["id"] = tool_call_id
                tool_call_ids.append(tool_call_id)

            model_responses_message_for_chat_history = f"[TOOL_CALLS]{json.dumps(parsed)}"
            model_responses = [{item["name"]: item["arguments"]} for item in parsed]
        except (json.JSONDecodeError, TypeError, KeyError):
            model_responses_message_for_chat_history = model_responses

        return {
            "model_responses": model_responses,
            "model_responses_message_for_chat_history": model_responses_message_for_chat_history,
            "tool_call_ids": tool_call_ids,
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
                "content": model_response_data["model_responses_message_for_chat_history"],
            }
        )
        return inference_data
