# LifeOS MCP
![alt text](image.png)

LifeOS MCP is a fast, local-first MCP server backed by SQLite. It exposes tools for notes, tasks, calendar, and a safe filesystem layer. It also includes resources, prompts, and templates for MCP clients.

## Core capabilities

- Notes: create, list, search, tag, pin, update, delete
- Tasks: create, update, search, complete, delete, status filtering
- Calendar: create, list, search, upcoming, update, delete
- Filesystem (allowlisted): search, list directories, read files
- Resources, prompts, templates for MCP clients

## 1) Local setup (project install)

Prerequisites:
- Python 3.12+
- Node 22.7.5+ and npm (for MCP Inspector)

Install:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:
```bash
cp .env.example .env
# edit as needed
```

Important defaults:
- SQLite DB at `data/lifeos.db`
- MCP endpoint at `/mcp`

## 2) MCP Inspector - STDIO (local MCP clients)

Run with Inspector (launches the server):
```bash
npx @modelcontextprotocol/inspector -- python -m app.run_mcp --transport stdio
```

Test from CLI:
```bash
npx @modelcontextprotocol/inspector --cli -- \
  python -m app.run_mcp --transport stdio --method tools/list
```

Optional health in STDIO:
```bash
HEALTH_ENABLED=true HEALTH_PORT=8080 python -m app.run_mcp --transport stdio
curl -s http://127.0.0.1:8080/health
```

## 3) MCP Inspector - HTTP (remote server)

Start the server:
```bash
python -m app.run_mcp --transport http --host 127.0.0.1 --port 8001
```

Start Inspector:
```bash
npx @modelcontextprotocol/inspector
```

In the Inspector UI:
- Transport: Streamable HTTP
- URL: `http://127.0.0.1:8001/mcp`

CLI test:
```bash
npx @modelcontextprotocol/inspector --cli http://127.0.0.1:8001/mcp \
  --transport http --method tools/list
```

Health check:
```bash
curl -s http://127.0.0.1:8001/health
```

## 4) Docker build image

```bash
docker build -t lifeos-mcp .
```

## 5) Docker + MCP Inspector - STDIO (local MCP clients)

Run Inspector and launch container in STDIO:
```bash
npx @modelcontextprotocol/inspector -- \
  docker run --rm -i lifeos-mcp python -m app.run_mcp --transport stdio
```

CLI test:
```bash
npx @modelcontextprotocol/inspector --cli -- \
  docker run --rm -i lifeos-mcp python -m app.run_mcp --transport stdio \
  --method tools/list
```

## 6) Docker + MCP Inspector - HTTP (remote server)

Run HTTP server:
```bash
mkdir -p data
docker run --rm -p 8000:8000 \
  -v $(pwd)/data:/data \
  -e PORT=8000 \
  -e SQLITE_DB_PATH="/data/lifeos.db" \
  -e ALLOWED_BASE_PATHS="/data" \
  lifeos-mcp
```

Inspector UI:
- Transport: Streamable HTTP
- URL: `http://127.0.0.1:8000/mcp`

CLI test:
```bash
npx @modelcontextprotocol/inspector --cli http://127.0.0.1:8000/mcp \
  --transport http --method tools/list
```

## 7) AWS EC2 quick deploy (HTTP)

1) Launch EC2 (Ubuntu 22.04 LTS).
2) Open inbound ports: 22 (SSH), 8000 (MCP HTTP).
3) SSH into the instance:
```bash
ssh -i /path/to/key.pem ubuntu@<EC2_PUBLIC_IP>
```

4) Install Docker:
```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo usermod -aG docker $USER
# log out and back in
```

5) Upload or clone the project:
```bash
git clone <YOUR_REPO_URL>
cd LifeOS
```

6) Build and run:
```bash
docker build -t lifeos-mcp .
mkdir -p /data/lifeos
docker run -d --name lifeos-mcp -p 8000:8000 \
  -v /data/lifeos:/data \
  -e PORT=8000 \
  -e SQLITE_DB_PATH="/data/lifeos.db" \
  -e ALLOWED_BASE_PATHS="/data" \
  lifeos-mcp
```

7) Verify locally on EC2:
```bash
curl -s http://127.0.0.1:8000/health
```

8) Connect from your machine:
- Inspector URL: `http://<EC2_PUBLIC_IP>:8000/mcp`

Tip: restrict Security Group inbound to your IP for safety.
