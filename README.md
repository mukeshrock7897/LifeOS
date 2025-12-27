# LifeOS MCP

This repo runs a Model Context Protocol (MCP) server using `fastmcp` with a local SQLite database.

## Core capabilities

- Notes: create, list, search, tag, pin, update, delete
- Tasks: create, update, search, complete, delete, status filtering
- Calendar: create, list, search, upcoming, update, delete
- Filesystem (allowlisted): search, list directories, read files

## 1) Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` (or export env vars):

```bash
cp .env.example .env
# then edit values
```

## 2) Run in STDIO mode (local MCP clients)

STDIO is for Claude Desktop / MCP Inspector / local clients.

```bash
python -m app.run_mcp --transport stdio
```

Optional health endpoint in STDIO mode:

```bash
HEALTH_ENABLED=true HEALTH_PORT=8080 python -m app.run_mcp --transport stdio
# GET http://127.0.0.1:8080/health
```

## 3) Run in HTTP mode (remote server)

```bash
python -m app.run_mcp --transport http --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl -s http://127.0.0.1:8000/health
```

MCP endpoint (default): `/mcp`

Many platforms set `PORT` automatically (Docker/Render/etc). In that case you can just:

```bash
PORT=8000 python -m app.run_mcp
```

## 4) Docker

Build:

```bash
docker build -t lifeos-mcp .
```

Run HTTP mode:

```bash
docker run --rm -p 8000:8000 \
  -v $(pwd)/data:/data \
  -e PORT=8000 \
  -e SQLITE_DB_PATH="/data/lifeos.db" \
  -e ALLOWED_BASE_PATHS="/app" \
  lifeos-mcp
```

Run STDIO mode (local only):

```bash
docker run --rm -i \
  -v $(pwd)/data:/data \
  -e SQLITE_DB_PATH="/data/lifeos.db" \
  lifeos-mcp
```

## 5) AWS EC2 quick deploy (HTTP)

1. Open the EC2 Security Group inbound rule for your port (e.g. 8000) from your IP.
2. On the instance:

```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo usermod -aG docker $USER
# log out / in
```

3. Copy project to the instance (or git clone), then:

```bash
docker build -t lifeos-mcp .
docker run -d --name lifeos-mcp -p 8000:8000 \
  -v /data:/data \
  -e PORT=8000 \
  -e SQLITE_DB_PATH="/data/lifeos.db" \
  -e ALLOWED_BASE_PATHS="/data" \
  lifeos-mcp
```
