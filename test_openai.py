from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path.cwd() / ".env")

client = OpenAI()

response = client.responses.create(
    model="gpt-5-mini",
    input="Explain what free cash flow means in two simple sentences."
)

print(response.output_text)