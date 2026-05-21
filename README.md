# ac-infinity-mcp

MCP server for [AC Infinity](https://acinfinity.com) grow environment control. Exposes device
readings, analytics, and write tools (speed, on/off) to Claude via the
[Model Context Protocol](https://modelcontextprotocol.io).

## Quick start — Claude Desktop

### 1. Install

```bash
pip install git+https://github.com/ober37/ac-infinity-mcp.git
```

Requires Python 3.11+. Install into a virtual environment to keep dependencies isolated:

```bash
python3 -m venv ~/.venvs/ac-infinity-mcp
source ~/.venvs/ac-infinity-mcp/bin/activate
pip install git+https://github.com/ober37/ac-infinity-mcp.git
which ac-infinity-mcp   # note this path — you'll need it below
```

### 2. Configure Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or
`%APPDATA%\Claude\claude_desktop_config.json` (Windows) and add:

```json
{
  "mcpServers": {
    "ac-infinity": {
      "command": "/path/to/ac-infinity-mcp",
      "env": {
        "AC_INFINITY_EMAIL": "you@example.com",
        "AC_INFINITY_PASSWORD": "yourpassword"
      }
    }
  }
}
```

Replace `/path/to/ac-infinity-mcp` with the full path printed by `which ac-infinity-mcp` above.

Restart Claude Desktop. You should see the AC Infinity tools available in the tool picker.

## Docker

### 1. Create `.env`

```bash
cp .env.example .env
# edit .env and fill in AC_INFINITY_EMAIL and AC_INFINITY_PASSWORD
```

### 2. Build and run

```bash
docker compose up --build
```

The container runs the MCP server over stdio. Connect a Claude Desktop instance (or any MCP
client) to it via a stdio bridge such as
[mcp-proxy](https://github.com/sparfenyuk/mcp-proxy).

> **Note:** `.env` is never copied into the image. Credentials are injected at runtime only
> via `env_file` in `docker-compose.yml`.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AC_INFINITY_EMAIL` | Yes | AC Infinity account email |
| `AC_INFINITY_PASSWORD` | Yes | AC Infinity account password |

## Available tools

| Tool | Description |
|------|-------------|
| `discover_devices` | List all controllers and their ports |
| `get_device_reading` | Current temp, humidity, VPD for a device |
| `get_all_device_readings` | Readings for all devices at once |
| `get_historical_readings` | Time-series data for a device |
| `check_vpd_drift` | VPD target compliance check |
| `get_environment_health` | Composite health score (0–100) + grade |
| `detect_environment_trends` | Linear trend + 7-day projection per metric |
| `get_port_activity_report` | Per-port on/off hours and uptime |
| `set_port_speed` | Set fan/pump speed (1–10, dry_run safe) |
| `set_port_on` | Turn a port on (dry_run safe) |
| `set_port_off` | Turn a port off (dry_run safe) |

Write tools default to `dry_run=True` — they return the payload they _would_ send without
making any changes. Pass `dry_run=False` to execute.

## Development

```bash
git clone https://github.com/ober37/ac-infinity-mcp.git
cd ac-infinity-mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in credentials
pytest tests/ -v
```

## License

MIT
