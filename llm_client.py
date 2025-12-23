import json
import re
import openai


def compare_dict_keys(d1, d2, ignore_case=True):
    def flatten_keys(d, parent_key="", ignore_case=True):
        keys = set()
        for k, v in d.items():
            k_norm = k.lower() if ignore_case else k
            new_key = f"{parent_key}_{k_norm}" if parent_key else k_norm
            keys.add(new_key)
            if isinstance(v, dict):
                keys |= flatten_keys(v, new_key, ignore_case=ignore_case)
        return keys

    keys1 = flatten_keys(d1, ignore_case=ignore_case)
    keys2 = flatten_keys(d2, ignore_case=ignore_case)

    return keys1 == keys2


class LLMClient:

    def __init__(
        self,
        # base_url="http://100.98.11.145:8000/v1",
        base_url="http://localhost:8000/v1",
        api_key="llama",
        model="llama",
        enable_thinking=False,
        max_try_time=3,
    ):
        self.model = model
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.enable_thinking = enable_thinking
        self.max_try_time = max_try_time
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0

    def reset_token_count(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0

    def get_token_usage(self):
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }

    def get_response(self, message):
        # return
        try:
            if "gpt" in self.model:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=message,
                    temperature=0.1,
                )
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=message,
                    temperature=0.1,
                    extra_body={"chat_template_kwargs": {"enable_thinking": self.enable_thinking}},
                )

            usage = response.usage
            self.prompt_tokens += int(usage.prompt_tokens)
            self.completion_tokens += int(usage.completion_tokens)
            self.total_tokens += int(usage.total_tokens)
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"{self.model} API call failed: {e}")
            return None

    def generate(self, message, response_format=None, choice_space=None):
        try_time = 0
        while try_time <= self.max_try_time:
            response = self.get_response(message)
            # print("Raw response:", response)
            try:
                json_part = re.search(r"\{\s*[\s\S]*?\s*\}", response)
                json_str = json_part.group(0)
                response = json.loads(json_str)
                if response_format:
                    assert compare_dict_keys(response, response_format)
                if choice_space:
                    assert response["choice"] in choice_space
            except Exception:
                try_time += 1
            else:
                return response
        return None


if __name__ == "__main__":
    client = LLMClient()
    messages = [{"role": "user", "content": "Hello!"}]
    res = client.generate(messages)
    print(res)
