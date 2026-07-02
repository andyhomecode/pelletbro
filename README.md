# pelletbro

A minimal self-hosted webhook service for [Petlibro](https://petlibro.com) smart feeders. Exposes a simple HTTP API so you can trigger feedings from Alexa (via IFTTT), Siri Shortcuts, Home Assistant, or anything else that can make an HTTP request.

The official Petlibro Alexa skill is widely reported as broken. This is the workaround.

## How it works

Pelletbro is a small [FastAPI](https://fastapi.tiangolo.com/) app that authenticates with the Petlibro cloud API (the same API the official app uses) and exposes a `/feed` endpoint you can call from any automation platform. It caches the auth token and handles re-authentication automatically.

## Requirements

- Docker + Docker Compose
- A Petlibro account and a supported feeder

## Setup

**1. Clone and configure**

```bash
git clone https://github.com/yourname/pelletbro
cd pelletbro
cp .env.example .env
```

Edit `.env` with your Petlibro email and password.

**2. Start the service**

```bash
docker compose up -d
```

**3. Find your device serial number**

```bash
curl http://localhost:8077/devices
```

Copy the `deviceSn` value from the response and add it to `.env` as `PETLIBRO_DEVICE_SN`, then restart:

```bash
docker compose restart
```

**4. Test it**

```bash
curl -X POST http://localhost:8077/feed
```

Your feeder should dispense food within a few seconds.

## Configuration

All configuration is via environment variables (`.env` file).

| Variable | Required | Description |
|---|---|---|
| `PETLIBRO_EMAIL` | Yes | Your Petlibro account email |
| `PETLIBRO_PASSWORD` | Yes | Your Petlibro account password |
| `PETLIBRO_DEVICE_SN` | No | Default device serial number. If unset, pass `?device_sn=` on each request |
| `API_KEY` | No | A secret key to protect the endpoints. Leave blank on a private network; set it if the service is reachable from the internet |

## API

Every response — success or error — includes a plain-English `message` field, so a client (like an iPhone Shortcut) can always read the same key regardless of outcome. On `/feed` failures caused by the feeder itself (offline, out of food, door error, etc.), `message` explains what's wrong rather than just relaying Petlibro's raw error code.

### `GET /feed`

Triggers a manual feeding.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `portions` | int | `1` | Number of portions to dispense (1–10) |
| `device_sn` | string | env var | Override the default device serial number |

```bash
# Default portions
curl http://localhost:8077/feed

# Custom portions
curl "http://localhost:8077/feed?portions=3"

# With API key
curl "http://localhost:8077/feed?api_key=your-api-key"
```

### `GET /devices`

Lists all devices associated with your Petlibro account. Useful for finding your `deviceSn`.

```bash
curl http://localhost:8077/devices
```

### `GET /status`

Plain-English health check for a feeder — handy for showing a result on an iPhone (Siri Shortcuts, notifications) without parsing raw Petlibro error codes.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `device_sn` | string | env var | Override the default device serial number |

```bash
curl "http://localhost:8077/status?api_key=your-api-key"
```

```json
{"device_sn": "AF01...", "online": false, "message": "second breakfast machine is offline — ..."}
```

### `GET /health`

Returns `{"ok": true}`. No authentication required. Use for uptime monitoring.

## Connecting to Alexa

Amazon removed native webhook support from Alexa Routines in 2023, so a skill intermediary is required. IFTTT used to be the easy option but now charges a monthly fee. The best free alternatives:

**Option A: AWS Lambda custom skill (recommended)**

Build a simple Lambda function (free tier: 1M requests/month) that calls your feed URL. Register it as a custom Alexa skill in the Alexa Developer Console. Once set up you say "Alexa, ask [skill name] to feed the cat."

**Option B: Node-RED**

Run [Node-RED](https://nodered.org/) in Docker, add the `node-red-contrib-alexa-remote2-applestrudel` node, and wire a voice command to an HTTP request node pointing at your feed URL. Setup is about 30 minutes but the Amazon session auth can occasionally need refreshing.

## Connecting to Siri

No third-party service needed — iOS Shortcuts can call HTTP endpoints directly and be triggered by Siri.

**1. Create the shortcut**

Open the **Shortcuts** app on your iPhone and tap **+** in the top right.

**2. Add a URL action**

Tap **Add Action**, search for **URL**, and select it. Enter your feed URL:
```
https://your-server/feed?api_key=your-api-key
```

**3. Add a Get Contents action**

Tap **+** below the URL action, search for **Get Contents of URL**, and select it. It will automatically use the URL from the previous step.

Tap the blue **Get Contents of** text to expand options and confirm:
- Method: **GET**

**4. (Optional) Show the actual result**

Every response includes a plain-English `message` field — showing it means you'll see *why* a feeding failed (feeder offline, out of food, etc.) instead of just "it didn't work."

Tap **+**, search for **Get Dictionary Value**, select it, and set the key to `message`. Then tap **+** again, search for **Show Notification**, and use the dictionary value as the notification text.

**5. Name and save**

Tap the shortcut name at the top (it will say "New Shortcut") and rename it to something Siri-friendly like **Feed the Cat**.

**6. Add to Siri**

Tap the **Share** icon (box with arrow) → **Add to Siri** → tap the red record button and say your phrase, e.g. *"feed the cat"* → tap **Done**.

You can now say **"Hey Siri, feed the cat"** from your iPhone, iPad, Apple Watch, or HomePod.

> **Tip:** On Apple Watch, you can also add the shortcut to a watch complication for one-tap feeding without saying anything.

## Security

- On a private home network with no external access, leaving `API_KEY` blank is fine.
- If the service is reachable from the internet (required for IFTTT), set `API_KEY` to a long random string. Generate one with `openssl rand -hex 32`.
- The service talks to `api.us.petlibro.com` over HTTPS. Your password is MD5-hashed before sending — this is Petlibro's own protocol, not something introduced here. The hash is never stored; it's computed at startup and kept only in memory.
- Consider putting the service behind a reverse proxy (nginx, Caddy, Traefik) with TLS if exposing publicly.

## Acknowledgements

The Petlibro API used here was reverse-engineered by the open source community:

- [jjjonesjr33/petlibro](https://github.com/jjjonesjr33/petlibro) — Home Assistant integration
- [praveensharma/HomebridgeLibro](https://github.com/praveensharma/HomebridgeLibro) — Homebridge plugin
- [Corti.com write-up](https://corti.com/bringing-petlibro-smart-feeders-to-apple-home-building-a-homebridge-plugin/) — API reverse engineering walkthrough

This project is not affiliated with or endorsed by Petlibro.

## License

[MIT](LICENSE)
