```bash
research_agent
cd E:\Downloads\codex\u42-agents\u42-agents\research_agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r .\requirements.txt

python agent.py "What is NVDA Stock rn"  
```

---
```bash
webapp
cd E:\Downloads\codex\u42-agents\u42-agents\web_app\ ; Remove-Item trading.db ; python.exe .\server.py

Remove-Item trading.db
```

---
```bash
finance_agent/agent

cd E:\Downloads\codex\u42-agents\u42-agents\finance_agent\agent\

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\.venv\Scripts\python.exe .\chat.py
```

---
```bash
cd E:\Downloads\codex\u42-agents\u42-agents\web_app\ ; Remove-Item trading.db ; python.exe .\server.py

cd "E:\Downloads\codex\u42-agents\u42-agents"
$env:A2A_BASE_URL = "http://127.0.0.1:8001"
python -m uvicorn research_agent.a2a_server:app --host 127.0.0.1 --port 8001

cd "E:\Downloads\codex\u42-agents\u42-agents"
$env:RESEARCH_A2A_URL = "http://127.0.0.1:8001"
Set-Location finance_agent/agent
.\.venv\Scripts\python.exe chat.py
```