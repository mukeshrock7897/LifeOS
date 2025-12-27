# LifeOS MCP
![alt text](image-1.png)

LifeOS MCP is a fast, local-first MCP server backed by SQLite. It exposes tools for notes, tasks, calendar, and a safe filesystem layer. It also includes resources, prompts, and templates for MCP clients.

## Core capabilities

- Notes: create, list, search, tag, pin, update, delete
- Tasks: create, update, search, complete, delete, status filtering
- Calendar: create, list, search, upcoming, update, delete
- Filesystem (allowlisted): search, list directories, read files
- Resources, prompts, templates for MCP clients

---

## 1) Local setup (project install)

Prerequisites:
- Python 3.12+
- Node 22.7.5+ and npm (for MCP Inspector)

Install:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
````

Create `.env`:

```bash
cp .env.example .env
# edit as needed
```

Important defaults:

* SQLite DB at `data/lifeos.db`
* MCP endpoint at `/mcp`

---

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

---

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

* Transport: Streamable HTTP
* URL: `http://127.0.0.1:8001/mcp`

CLI test:

```bash
npx @modelcontextprotocol/inspector --cli http://127.0.0.1:8001/mcp \
  --transport http --method tools/list
```

Health check:

```bash
curl -s http://127.0.0.1:8001/health
```

---

## 4) Docker build image

```bash
docker build -t lifeos-mcp .
```

---

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

---

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

* Transport: Streamable HTTP
* URL: `http://127.0.0.1:8000/mcp`

CLI test:

```bash
npx @modelcontextprotocol/inspector --cli http://127.0.0.1:8000/mcp \
  --transport http --method tools/list
```

Health check:

```bash
curl -s http://127.0.0.1:8000/health
```

---

## 7) AWS EC2 quick deploy (HTTP) ✅ (fastest)

This exposes HTTP on port `8000`. Great for testing.

1. Launch EC2 (Ubuntu 22.04/24.04).

2. Open inbound ports in Security Group:

   * 22 (SSH) -> your IP
   * 8000 (MCP HTTP) -> your IP (recommended) or 0.0.0.0/0 (public)

3. SSH into the instance:

```bash
ssh -i /path/to/key.pem ubuntu@<EC2_PUBLIC_IP>
```

> Mac key fix if you see “UNPROTECTED PRIVATE KEY FILE”:

```bash
chmod 400 /path/to/key.pem
```

4. Install Docker + Git:

```bash
sudo apt-get update
sudo apt-get install -y docker.io git
sudo usermod -aG docker $USER
newgrp docker
```

> If you see: “permission denied while trying to connect to the Docker daemon socket”
> logout/login or run `newgrp docker`.

5. Clone the project:

```bash
git clone https://github.com/mukeshrock7897/LifeOS.git
cd LifeOS
```

6. Build and run:

```bash
docker build -t lifeos-mcp .
sudo mkdir -p /data/lifeos

docker run -d --name lifeos-mcp -p 8000:8000 \
  -v /data/lifeos:/data \
  -e PORT=8000 \
  -e SQLITE_DB_PATH="/data/lifeos.db" \
  -e ALLOWED_BASE_PATHS="/data" \
  --restart unless-stopped \
  lifeos-mcp
```

7. Verify locally on EC2:

```bash
curl -s http://127.0.0.1:8000/health
```

8. Connect from your machine:

* Inspector URL: `http://<EC2_PUBLIC_IP>:8000/mcp`
* Health URL: `http://<EC2_PUBLIC_IP>:8000/health`

---

## 8) AWS EC2 production deploy (Domain + HTTPS) ✅ (recommended for public use)

This gives you clean URLs like:

* `https://mcp.lifeos.me.uk/health`
* `https://mcp.lifeos.me.uk/mcp`

### 8.1) Allocate Elastic IP (static IP)

EC2 -> Elastic IPs -> Allocate -> **Associate** to your EC2 instance.

Example Elastic IP:

* `54.156.184.191`

### 8.2) Route53 DNS (Hosted zone + A record)

1. Route53 -> Hosted zones -> Create hosted zone:

   * Domain: `lifeos.me.uk`
   * Type: Public hosted zone

2. Create an A record for the MCP subdomain:

   * Record name: `mcp`
   * Type: `A`
   * Value: `<YOUR_ELASTIC_IP>` (e.g. `54.156.184.191`)
   * TTL: 300

Now:

* `mcp.lifeos.me.uk` -> `<YOUR_ELASTIC_IP>`

3. IMPORTANT (domain delegation):
   If your domain is registered in Route53:
   Route53 -> Domains -> Registered domains -> `lifeos.me.uk` -> **Name servers**
   ✅ Ensure the Registered domain name servers match the Hosted zone NS record.

### 8.3) Verify DNS before SSL

Run (from EC2 or your laptop):

```bash
dig mcp.lifeos.me.uk A @8.8.8.8 +short
```

Expected output:

* `<YOUR_ELASTIC_IP>`

(Optional direct hosted-zone check):

```bash
dig @<ONE_OF_YOUR_ROUTE53_NS> mcp.lifeos.me.uk A +short
```

### 8.4) Open ports 80 & 443 (Security Group)

Inbound rules:

* 22 (SSH) -> your IP
* 80 (HTTP) -> 0.0.0.0/0
* 443 (HTTPS) -> 0.0.0.0/0

> After HTTPS works, you can remove public port 8000.

### 8.5) Run Docker app on localhost only (secure)

Stop old container (if any):

```bash
docker stop lifeos-mcp 2>/dev/null || true
docker rm lifeos-mcp 2>/dev/null || true
```

Run container bound to localhost:

```bash
sudo mkdir -p /data/lifeos

docker run -d --name lifeos-mcp -p 127.0.0.1:8000:8000 \
  -v /data/lifeos:/data \
  -e PORT=8000 \
  -e SQLITE_DB_PATH="/data/lifeos.db" \
  -e ALLOWED_BASE_PATHS="/data" \
  --restart unless-stopped \
  lifeos-mcp
```

Verify on EC2:

```bash
curl -s http://127.0.0.1:8000/health
```

### 8.6) Install Nginx + Certbot

```bash
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

### 8.7) Nginx reverse proxy config

Create file:

```bash
sudo nano /etc/nginx/sites-available/lifeos
```

Paste:

```nginx
server {
  listen 80;
  server_name mcp.lifeos.me.uk;

  location / {
    proxy_pass http://127.0.0.1:8000;

    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    proxy_buffering off;
    proxy_read_timeout 3600;
  }
}
```

Enable + reload:

```bash
sudo ln -sf /etc/nginx/sites-available/lifeos /etc/nginx/sites-enabled/lifeos
sudo nginx -t
sudo systemctl reload nginx
```

Test HTTP (must work before certbot):

```bash
curl -I http://mcp.lifeos.me.uk
curl -s http://mcp.lifeos.me.uk/health
```

### 8.8) Issue SSL cert (Let’s Encrypt)

```bash
sudo certbot --nginx -d mcp.lifeos.me.uk --agree-tos -m your-email@gmail.com --redirect
```

Test HTTPS:

```bash
curl -s https://mcp.lifeos.me.uk/health
```

✅ Final remote URLs:

* Health: `https://mcp.lifeos.me.uk/health`
* MCP: `https://mcp.lifeos.me.uk/mcp`

### 8.9) Security cleanup (recommended)

* Remove inbound rule for **8000** from the Security Group (keep only 80/443).
* Keep Docker bound to `127.0.0.1:8000` as shown above.

---

## 9) Add Remote MCP server to Claude

Once HTTPS is working, use:

* `https://mcp.lifeos.me.uk/mcp`

In Claude:

* Settings -> Connectors -> Add custom MCP server
* Paste the URL above

---

## 10) Troubleshooting (most common issues)

### Docker: permission denied to docker.sock

```bash
sudo usermod -aG docker $USER
newgrp docker
docker ps
```

### SSH key: “UNPROTECTED PRIVATE KEY FILE”

```bash
chmod 400 /path/to/key.pem
```

### DNS: SERVFAIL / not resolving

Check:

```bash
dig mcp.lifeos.me.uk A @8.8.8.8 +short
dig NS lifeos.me.uk +short
```

Fix:

* Ensure Route53 A record exists
* Ensure Registered domain Name servers match Hosted zone NS

### Certbot: timeout during connect (HTTP challenge)

Reason: port 80 blocked.
Fix:

* Security Group inbound: allow 80 from 0.0.0.0/0
* Verify:

```bash
curl -I http://mcp.lifeos.me.uk
```

### Nginx works but /health hangs

Check logs:

```bash
sudo tail -n 50 /var/log/nginx/error.log
docker logs -n 80 lifeos-mcp
```

---

## 11) Operations (update deploy)

Pull latest + rebuild + restart:

```bash
cd ~/LifeOS
git pull
docker build -t lifeos-mcp .

docker stop lifeos-mcp
docker rm lifeos-mcp

docker run -d --name lifeos-mcp -p 127.0.0.1:8000:8000 \
  -v /data/lifeos:/data \
  -e PORT=8000 \
  -e SQLITE_DB_PATH="/data/lifeos.db" \
  -e ALLOWED_BASE_PATHS="/data" \
  --restart unless-stopped \
  lifeos-mcp

sudo systemctl reload nginx
```

Logs:

```bash
docker logs -f lifeos-mcp
sudo tail -n 50 /var/log/nginx/error.log
```

---

## 12) Final checklist (copy-paste)

DNS:

```bash
dig mcp.lifeos.me.uk A @8.8.8.8 +short
```

HTTP reachable:

```bash
curl -I http://mcp.lifeos.me.uk
```

HTTPS OK:

```bash
curl -s https://mcp.lifeos.me.uk/health
```

MCP endpoint:

* `https://mcp.lifeos.me.uk/mcp`

```
