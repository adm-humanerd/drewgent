<p align="center">
  <img src="assets/banner.png" alt="Drewgent Agent" width="100%">
</p>

# Drewgent Agent ☤

> **⚠️ NOTE:** Drewgent is a **fork of [Hermes-Agent](https://github.com/adm-humanerd/hermes-agent)** by Nous Research, optimized for constrained environments and extended with Knowledge Bus & Feedback Loop.

<p align="center">
  <a href="https://github.com/adm-humanerd/drewgent"><img src="https://img.shields.io/badge/Fork%20of-Hermes--Agent-orange?style=for-the-badge" alt="Fork of Hermes-Agent"></a>
  <a href="https://github.com/adm-humanerd/drewgent/blob/main/docs/DREWGENT_ARCHITECTURE.md"><img src="https://img.shields.io/badge/Docs-Architecture-FFD700?style=for-the-badge" alt="Documentation"></a>
  <a href="https://discord.gg/NousResearch"><img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://github.com/adm-humanerd/drewgent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://humanerd.ai"><img src="https://img.shields.io/badge/Built%20by-HUMANERD-blueviolet?style=for-the-badge" alt="Built by HUMANERD"></a>
</p>

**Drewgent** is a self-improving AI agent built by [HUMANERD](https://humanerd.ai). Built on Hermes-Agent, it features a built-in **Knowledge Bus** and **Feedback Loop** — every response is verified, stored, and used to improve future responses.

## Why Drewgent?

While Hermes-Agent is a general-purpose agent, Drewgent (a fork) is **optimized for limited environments** (like a $5 VPS or home lab). It includes:

- **Docker-First Architecture**: Pre-built images, no `git clone` required
- **Local Monitoring**: Hourly Discord notifications without external services
- **Knowledge Bus**: Patterns learned from experience persist across sessions
- **Built-in Verification**: Quality gates catch hallucinations before they happen

## The Story Behind Drewgent

Drewgent was born from solving real problems in constrained environments:

### The Journey

```
💀 Problem: "Docker build times out on Colima"
   ↓
💡 Solution: Use pre-built images, volume mount for code changes
   
💀 Problem: "Need to monitor the agent but no external services"
   ↓
💡 Solution: Custom monitor script → Discord webhook
   
💀 Problem: "Tailscale DNS intercepts all DNS queries"
   ↓
💡 Solution: Monitor runs in Docker, health checks via localhost
   
💀 Problem: "Cloudflare Tunnel created in wrong account"
   ↓
💡 Solution: Docker Hub images + local monitoring = no tunnel needed
   
💀 Problem: "How to improve agent over time?"
   ↓
💡 Solution: Knowledge Bus + Verification Engine + Feedback Loop
```

### Key Optimizations

| Problem | Solution |
|---------|----------|
| Docker build timeout (Colima 120s) | Pre-built images on Docker Hub |
| Mac DNS intercepted by Tailscale | Docker network_mode: host + localhost checks |
| No external monitoring available | Custom Discord monitor script |
| Agent doesn't learn from mistakes | Knowledge Bus stores verification results |
| Multiple services, complex setup | docker-compose.yml with restart: unless-stopped |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Drewgent Agent                          │
├─────────────────────────────────────────────────────────────┤
│  Gateway → Agent → Knowledge Bus ← Verification Engine     │
│                              ↑                               │
│                          Growth Engine                        │
│                              ↑                               │
│                          Revision Loop                        │
└─────────────────────────────────────────────────────────────┘
```

### The Feedback Loop

Drewgent doesn't just respond — it **learns**:

1. **Verification**: Every response is checked for quality (Korean language priority, hallucination detection, completeness)
2. **Storage**: Failed checks are stored in Knowledge Bus
3. **Query**: Future verifications query past patterns
4. **Improvement**: The agent gets better over time

## Quick Start

### Prerequisites
- Docker & Docker Compose
- API keys (Anthropic, OpenAI, MiniMax)
- Discord webhook (optional, for monitoring)

### Installation

```bash
# 1. Pull the image (no git clone needed!)
docker pull humanerdkr/drewgent:latest

# 2. Create directory
mkdir -p data

# 3. Create .env file
cat > .env << 'EOF'
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key
MINIMAX_API_KEY=your_key
DREW_DISCORD_WEBHOOK=https://discord.com/api/webhooks/YOUR_WEBHOOK
EOF

# 4. Copy docker-compose.yml
cp docker-compose.yml.example docker-compose.yml

# 5. Start
docker-compose up -d
```

That's it. No `git clone`, no dependency installation, no build steps.

> **⚠️ SECURITY:** Never commit your `.env` file or `docker-compose.yml` with real API keys. The example file uses environment variables — keep your secrets safe!

## Docker Images

| Image | Description | Pull Command |
|-------|-------------|--------------|
| `humanerdkr/drewgent:latest` | Gateway + Agent | `docker pull humanerdkr/drewgent:latest` |
| `humanerdkr/drewgent-monitor:latest` | Discord Monitor | `docker pull humanerdkr/drewgent-monitor:latest` |

### Rename as You Like

```bash
# Pull and rename to your brand
docker pull humanerdkr/drewgent:latest
docker tag humanerdkr/drewgent:latest my-cool-agent:latest
```

## Monitoring

The Monitor service sends hourly reports to Discord:

- **Health Status**: Is the gateway alive?
- **Verification Stats**: Pass rate, average score, P0 blocks
- **Knowledge Bus**: Patterns learned, growth over time
- **Morning Summary**: 8 AM report of midnight-to-8AM activity

```
⏰ Every hour (except midnight-8AM): Full metrics report
🌅 8 AM: Night summary
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /v1/metrics` | Verification metrics |
| `GET /v1/knowledge` | Knowledge Bus data |
| `GET /v1/models` | Available models |

## Troubleshooting

### "No module named 'drewgent_constants'"

Fixed in the Docker image. Make sure you're using the latest:
```bash
docker pull humanerdkr/drewgent:latest
```

### "Docker build times out"

Don't build locally — use the pre-built image:
```bash
docker pull humanerdkr/drewgent:latest
```

### "Monitor can't reach gateway"

Make sure all services use `network_mode: host` for localhost access.

## Documentation

- [Architecture Guide](./docs/DREWGENT_ARCHITECTURE.md) - Full architecture, module connections, optimization decisions
- [Knowledge Bus](./docs/PDCA_KNOWLEDGE_BUS.md) - How the feedback loop works
- [Development Guide](./AGENTS.md) - For contributors

## Lessons Learned

Building Drewgent taught us important lessons about **constrained environments**:

1. **Pre-built images > local builds**: Colima's 120s timeout makes local builds unreliable
2. **Docker networking quirks**: `network_mode: host` avoids Docker's DNS issues
3. **VPNs can break DNS**: Tailscale intercepts all DNS queries by default
4. **Cloudflare Tunnel account isolation**: Always verify which account you're using
5. **Feedback loops improve quality**: Storing verification results makes the agent smarter over time

## Security

### Best Practices

1. **Never commit secrets**: Your `.env` file contains API keys — never commit it to version control
2. **Use environment variables**: All secrets are loaded from `.env` or environment variables
3. **Docker secrets**: Use Docker secrets or environment variables for sensitive data in production

### Files You Need to Create

| File | Contains | GitHub |
|------|----------|--------|
| `.env` | API keys, webhook URLs | ❌ Never commit |
| `docker-compose.yml` | Service config | ✅ Use example |
| `~/.drewgent/` | User config, memories | ❌ Never commit |

## License

MIT License - HUMANERD
