# SafeRunner

Auditable, zero-retention AI analysis of financial filings.  
No data stored. Container destroyed after task. Input hash verified.

## Why It Matters

Most AI tools hallucinate and hide their inputs.  
SafeRunner delivers high-risk professional automation **with verifiable trust**:

## What It Does

- **Input**: Machine-readable financial document (PDF or SEC HTML)  
- **Output**: Structured JSON with risk summary + full audit log  
- **Audit Trail**: input hash, token usage, timestamps, step status  
- **Privacy**: Zero retention. Full pipeline reproducible.

## Try It

A sample NVIDIA FY2025 10-K filing is included:

- File: [`samples/nvda-2025-10k.htm`](samples/nvda-2025-10k.htm)  
- SHA256: `c46f21be4a2293234a5e8d9b0ede6056a89f127d9a4a7945448daa3692903826`

To run:
```bash
git clone https://github.com/yourname/safe-runner.git
cd safe-runner
pip install -r requirements.txt
cp .env.example .env  # add your DashScope API key
python main.py
```
Output appears in results/sr-*.json.
Verify input integrity:
```bash
sha256sum samples/nvda-2025-10k.htm
# Expected: c46f21be4a2293234a5e8d9b0ede6056a89f127d9a4a7945448daa3692903826
```
