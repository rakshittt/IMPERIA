from openai import OpenAI
import os
from dotenv import load_dotenv
from tradingagents.dataflows.news_knowledge_brain import NewsKnowledgeBrain

load_dotenv()

# First get some recent news for Nvidia using our new NewsKnowledgeBrain
print("Fetching recent news for NVDA...")
news_data = NewsKnowledgeBrain.get_company_news("NVIDIA")

if not news_data:
    # Fallback to general search if news APIs didn't return anything
    news_data = NewsKnowledgeBrain.web_search("recent NVIDIA stock news")

print("News retrieved from:", news_data.get("source") if news_data else "None")

# Limit news context to first 3 articles to save tokens and avoid timeouts
if news_data and "articles" in news_data:
    news_data["articles"] = news_data["articles"][:3]

news_context = str(news_data) if news_data else "No specific news found."


client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = "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"
)

user_prompt = f"""
I have 10 stocks of Nvidia (NVDA). Please analyze my portfolio based on this recent news:

{news_context}
"""

print("\nSending prompt to NVIDIA API (deepseek-ai/deepseek-v4-pro)...")
completion = client.chat.completions.create(
  model="deepseek-ai/deepseek-v4-pro",
  messages=[{"role":"user","content":user_prompt}],
  temperature=1,
  top_p=0.95,
  max_tokens=16384,
  extra_body={"chat_template_kwargs":{"thinking":False}},
  stream=True
)

for chunk in completion:
  if not getattr(chunk, "choices", None):
    continue
  if chunk.choices and chunk.choices[0].delta.content is not None:
    print(chunk.choices[0].delta.content, end="", flush=True)

print("\n")
