# AminekGoGo

Local Pokémon GO spawn radar. Fan-made community tool — not affiliated with Niantic or Nintendo.

## Run locally

```bash
python server.py
```

Open http://localhost:8000

Leave `config.js` empty. The Python server proxies the live spawn feed and place search same-origin.

## Host on GitHub Pages (with live scans)

GitHub Pages cannot run Python, so live spawns need a free Cloudflare Worker as a CORS proxy.

### 1. Deploy the Worker

1. Create a free [Cloudflare](https://dash.cloudflare.com/sign-up) account.
2. Install Wrangler once: `npm install -g wrangler`
3. From this folder:

```bash
wrangler login
wrangler deploy
```

Copy the Worker URL it prints (looks like `https://aminekgogo-api.<you>.workers.dev`).

### 2. Point the site at the Worker

Edit `config.js`:

```js
window.AMINEKGOGO_API_BASE = "https://aminekgogo-api.YOUR_SUBDOMAIN.workers.dev";
```

### 3. Publish to GitHub Pages

1. Push this repo to GitHub.
2. Settings → Pages → Source: Deploy from a branch → `main` / root (or `/docs` if you prefer).
3. Open `https://YOUR_USER.github.io/YOUR_REPO/`

Live map, place search, World hotspots, and Show everything should all work.

## What’s included

- Live map scan around a pin (up to 25 km)
- World hotspots index
- “Show everything” scan across known hotspots
- IV / CP filters

## Privacy notes before publishing

- Do **not** commit `.env`, `providers.json`, API keys, or account credentials.
- Browser localStorage (saved locations, favorites, filters) stays on the visitor’s machine and is never uploaded by this app.
- Spawn data comes from third-party community feeds and may be incomplete or inaccurate.

## License

Add a license if you want others to reuse this (for example MIT). Without one, others should assume they need your permission.
