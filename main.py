import json
import hashlib
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from dashscope import Generation

try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

load_dotenv()

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    raise ValueError(
        "❌ DASHSCOPE_API_KEY is not set.\n"
        "Please create a `.env` file and add your API key.\n"
        "See `.env.example` for reference."
    )

MODEL = config["model"]
DOCUMENT_PATH = config["document_path"]

def extract_text_from_pdf(pdf_path: str) -> str:
    if not HAS_PDF:
        raise ImportError("Please install pdfplumber: pip install pdfplumber")
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:10]: 
            t = page.extract_text()
            if t:
                text += t + "\n"
    return text.strip()


def extract_text_from_html_file(html_path: str) -> str:
    if not HAS_BS4:
        raise ImportError("Please install beautifulsoup4: pip install beautifulsoup4")
    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    soup = BeautifulSoup(content, 'html.parser')
    for tag in soup(["script", "style", "header", "footer", "nav", "aside", "comment"]):
        tag.decompose()
    lines = [line.strip() for line in soup.get_text().split('\n') if line.strip()]
    return '\n'.join(lines)


def call_qwen(prompt: str):
    print("🧠 Calling Qwen...")
    response = Generation.call(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        api_key=DASHSCOPE_API_KEY,
        temperature=0.0,
        result_format="message"
    )
    if response.status_code != 200:
        raise Exception(f"Qwen error: {response}")
    content = response.output.choices[0].message["content"]
    usage = response.usage
    print(f"✅ Qwen response ({usage.input_tokens} → {usage.output_tokens} tokens)")
    return content, usage


def main():
    session_id = f"sr-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    print(f"🚀 Starting SafeRunner (local file mode) | ID: {session_id}")

    if not os.path.exists(DOCUMENT_PATH):
        raise FileNotFoundError(f"❌ File not found: {os.path.abspath(DOCUMENT_PATH)}")

    with open(DOCUMENT_PATH, "rb") as f:
        file_bytes = f.read()
        input_hash = hashlib.sha256(file_bytes).hexdigest()

    if DOCUMENT_PATH.lower().endswith('.pdf'):
        full_text = extract_text_from_pdf(DOCUMENT_PATH)
    elif DOCUMENT_PATH.lower().endswith(('.html', '.htm')):
        full_text = extract_text_from_html_file(DOCUMENT_PATH)
    else:
        raise ValueError("Only .pdf, .html, and .htm files are supported.")

    print(f"🔖 Hash: {input_hash[:16]}...")
    print(f"📄 Extracted {len(full_text)} characters")

    prompt = f"""
You are a financial analyst. Summarize the core content of the following document and highlight any potential risks or key issues.
Output ONLY valid JSON in the format: {{"summary": "...", "key_risks": ["...", "..."]}}

Document content:
{full_text[:12000]}
"""

    result_str, usage = call_qwen(prompt)

    try:
        result = json.loads(result_str)
    except json.JSONDecodeError:
        result = {"raw_output": result_str}

    output = {
        "session_id": session_id,
        "input_source": os.path.abspath(DOCUMENT_PATH),
        "input_hash_sha256": input_hash,
        "execution_log": {
            "steps": [
                {"step": "load_local_file", "status": "success"},
                {"step": "extract_text", "char_count": len(full_text)},
                {"step": "llm_call", "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens}
            ],
            "completed_at": datetime.now(timezone.utc).isoformat()
        },
        "analysis": result
    }

    os.makedirs("results", exist_ok=True)
    output_file = f"results/{session_id}_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n🎉 Success! Result saved to: {os.path.abspath(output_file)}")


if __name__ == "__main__":
    main()