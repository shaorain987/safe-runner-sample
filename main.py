import json
import hashlib
import os
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


with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

DASHSCOPE_API_KEY = config["dashscope_api_key"]
MODEL = config["model"]
DOCUMENT_PATH = config["document_path"]  


def extract_text_from_pdf(pdf_path: str) -> str:
    if not HAS_PDF:
        raise ImportError("请安装 pdfplumber: pip install pdfplumber")
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:10]: 
            t = page.extract_text()
            if t:
                text += t + "\n"
    return text.strip()


def extract_text_from_html_file(html_path: str) -> str:
    if not HAS_BS4:
        raise ImportError("请安装 beautifulsoup4: pip install beautifulsoup4")
    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    soup = BeautifulSoup(content, 'html.parser')
    for tag in soup(["script", "style", "header", "footer", "nav", "aside", "comment"]):
        tag.decompose()
    lines = [line.strip() for line in soup.get_text().split('\n') if line.strip()]
    return '\n'.join(lines)


def call_qwen(prompt: str):
    print("🧠 调用 Qwen...")
    response = Generation.call(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        api_key=DASHSCOPE_API_KEY,
        temperature=0.0,
        result_format="message"
    )
    if response.status_code != 200:
        raise Exception(f"Qwen 错误: {response}")
    content = response.output.choices[0].message["content"]
    usage = response.usage
    print(f"✅ Qwen 返回 ({usage.input_tokens} → {usage.output_tokens} tokens)")
    return content, usage


def main():
    session_id = f"sr-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    print(f"🚀 启动 SafeRunner (本地文件模式) | ID: {session_id}")

    if not os.path.exists(DOCUMENT_PATH):
        raise FileNotFoundError(f"❌ 文件不存在: {os.path.abspath(DOCUMENT_PATH)}")

    with open(DOCUMENT_PATH, "rb") as f:
        file_bytes = f.read()
        input_hash = hashlib.sha256(file_bytes).hexdigest()

    if DOCUMENT_PATH.lower().endswith('.pdf'):
        full_text = extract_text_from_pdf(DOCUMENT_PATH)
    elif DOCUMENT_PATH.lower().endswith(('.html', '.htm')):
        full_text = extract_text_from_html_file(DOCUMENT_PATH)
    else:
        raise ValueError("仅支持 .pdf / .html / .htm 文件")

    print(f"🔖 哈希: {input_hash[:16]}...")
    print(f"📄 提取 {len(full_text)} 字")

    prompt = f"""
你是一位分析师。请总结以下文档的核心内容，并指出任何潜在风险或重要事项。
仅输出 JSON，格式：{{"summary": "...", "key_risks": ["...", "..."]}}

文档内容：
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

    print(f"\n🎉 成功！结果已保存至: {os.path.abspath(output_file)}")


if __name__ == "__main__":
    main()