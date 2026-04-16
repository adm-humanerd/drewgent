<p align="center">
  <img src="assets/banner.png" alt="Drewgent Agent" width="100%">
</p>

# Drewgent Agent ☤

<p align="center">
  <a href="https://github.com/adm-humanerd/drewgent/blob/main/docs/DREWGENT_ARCHITECTURE.md"><img src="https://img.shields.io/badge/Docs-Architecture-FFD700?style=for-the-badge" alt="Documentation"></a>
  <a href="https://discord.gg/NousResearch"><img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://github.com/adm-humanerd/drewgent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://humanerd.ai"><img src="https://img.shields.io/badge/Built%20by-HUMANERD-blueviolet?style=for-the-badge" alt="Built by HUMANERD"></a>
</p>

**Drewgent** is a self-improving AI agent built by [HUMANERD](https://humanerd.ai). It features a built-in **Knowledge Bus** and **Feedback Loop** — every response is verified, stored, and used to improve future responses.

## Key Features

| Feature | Description |
|---------|-------------|
| **Knowledge Bus** | Central knowledge store with pattern recognition |
| **Feedback Loop** | Verification → Knowledge → Better decisions |
| **Verification Engine** | Quality gates with Korean language priority, hallucination detection |
| **Revision Loop** | Automatic response revision when quality thresholds aren't met |
| **Docker-First** | Pre-built images for easy deployment anywhere |
| **Local Monitoring** | Hourly Discord notifications with metrics |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Drewgent Agent                            │
├─────────────────────────────────────────────────────────────┤
│  Gateway → Agent → Knowledge Bus ← Verification Engine       │
│                              ↑                               │
│                          Growth Engine                       │
│                              ↑                               │
│                          Revision Loop                      │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start (Docker)

```bash
# 1. Create directory
mkdir -p data

# 2. Create .env file
cat > .env << 'EOF'
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key
MINIMAX_API_KEY=your_key
DREW_DISCORD_WEBHOOK=https://discord.com/api/webhooks/YOUR_WEBHOOK
EOF

# 3. Create docker-compose.yml (see below)

# 4. Start
docker-compose up -d
```

## Docker Compose

```yaml
services:
  drewgent-gateway:
    image: humanerdkr/drewgent:latest
    container_name: drewgent-gateway
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./data:/opt/data
      - ~/.drewgent:/root/.drewgent:rw
    env_file:
      - .env
    environment:
      - HERMES_HOME=/opt/data
      - PYTHONPATH=/opt/drewgent
    entrypoint: ["bash", "-c", "cd /opt/drewgent && mkdir -p /opt/data && exec python3 -m drewgent_cli.main gateway run"]

  drewgent-agent:
    image: humanerdkr/drewgent:latest
    container_name: drewgent-agent
    restart: unless-stopped
    network_mode: host
    entrypoint: ["bash", "-c", "cd /opt/drewgent && mkdir -p /opt/data && exec python3 cli.py agent run"]
    volumes:
      - ./data:/opt/data
      - ~/.drewgent:/root/.drewgent:rw
    env_file:
      - .env
    depends_on:
      - drewgent-gateway

  monitor:
    image: humanerdkr/drewgent-monitor:latest
    container_name: drewgent-monitor
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./data:/opt/data
    environment:
      - GATEWAY_URL=http://localhost:8642
      - DREW_DISCORD_WEBHOOK=https://discord.com/api/webhooks/YOUR_WEBHOOK
```

## Docker Images

| Image | Pull Command |
|-------|--------------|
| `humanerdkr/drewgent:latest` | `docker pull humanerdkr/drewgent:latest` |
| `humanerdkr/drewgent-monitor:latest` | `docker pull humanerdkr/drewgent-monitor:latest` |

**Rename as you like:**
```bash
docker pull humanerdkr/drewgent:latest
docker tag humanerdkr/drewgent:latest my-agent:latest
```

## Monitoring

The Monitor service sends hourly reports to Discord:
- Gateway health status
- Verification statistics (pass rate, scores, P0 blocks)
- Knowledge Bus growth
- Morning summary at 8 AM

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /v1/metrics` | Verification metrics |
| `GET /v1/knowledge` | Knowledge Bus data |
| `GET /v1/models` | Available models |

## Documentation

- [Architecture Guide](./docs/DREWGENT_ARCHITECTURE.md) - Full architecture and implementation details
- [Knowledge Bus](./docs/PDCA_KNOWLEDGE_BUS.md) - Knowledge Bus implementation
- [Development Guide](./AGENTS.md) - For contributors

## License

MIT License - HUMANERD
