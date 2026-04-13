import os
from openai import OpenAI

api_key = "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"
if not api_key:
    raise RuntimeError("请先设置环境变量 NVIDIA_API_KEY")

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=api_key,
)

resp = client.chat.completions.create(
    model="z-ai/glm4.7",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "请用中文介绍一下你自己。"},
    ],
    temperature=0.2,
    max_tokens=1024,
    stream=False,
)

print(resp.choices[0].message.content)