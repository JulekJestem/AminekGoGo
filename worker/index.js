/**
 * Cloudflare Worker proxy for AminekGoGo.
 * Bypasses browser CORS so GitHub Pages can reach the live spawn feed.
 */
const UPSTREAM = "https://pokecoords.iflowgo.com/iflowgopokecoords/api/v1/nearby";
const PHOTON = "https://photon.komoot.io/api/";
const ALLOWED = new Set(["lat", "lon", "radius_km", "layers", "limit"]);

function corsHeaders(request) {
  const origin = request.headers.get("Origin") || "*";
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Accept, Content-Type",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

function json(payload, status, request) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      ...corsHeaders(request),
    },
  });
}

async function handleNearby(url, request) {
  const query = {};
  for (const key of ALLOWED) {
    const value = url.searchParams.get(key);
    if (value != null && value !== "") query[key] = value;
  }

  try {
    const lat = Number(query.lat);
    const lon = Number(query.lon);
    const radius = Number(query.radius_km ?? 25);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
      throw new Error("lat and lon are required");
    }
    if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      throw new Error("Coordinates are out of range");
    }
    if (radius < 1 || radius > 25) {
      throw new Error("Radius must be between 1 and 25 km");
    }
    query.layers = "spawns";
    query.limit = "800";
  } catch (error) {
    return json({ error: String(error.message || error) }, 400, request);
  }

  const upstream = `${UPSTREAM}?${new URLSearchParams(query)}`;
  try {
    const response = await fetch(upstream, {
      headers: {
        Accept: "application/json",
        "User-Agent": "AminekGoGo Cloudflare Worker",
      },
    });
    const body = await response.arrayBuffer();
    return new Response(body, {
      status: response.status,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
        ...corsHeaders(request),
      },
    });
  } catch (error) {
    return json({ error: `Could not reach iFlowGo: ${error}` }, 502, request);
  }
}

async function handleGeocode(url, request) {
  const q = (url.searchParams.get("q") || "").trim().slice(0, 160);
  if (q.length < 2) {
    return json({ error: "Enter at least two characters to search." }, 400, request);
  }

  const upstream = `${PHOTON}?${new URLSearchParams({ q, limit: "5", lang: "en" })}`;
  try {
    const response = await fetch(upstream, {
      headers: {
        Accept: "application/json",
        "User-Agent": "AminekGoGo/1.0 (GitHub Pages spawn radar)",
      },
    });
    const body = await response.arrayBuffer();
    return new Response(body, {
      status: response.status,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
        ...corsHeaders(request),
      },
    });
  } catch (error) {
    return json({ error: `Could not reach place search: ${error}` }, 502, request);
  }
}

export default {
  async fetch(request) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(request) });
    }
    if (request.method !== "GET") {
      return json({ error: "Method not allowed" }, 405, request);
    }

    const url = new URL(request.url);
    if (url.pathname === "/" || url.pathname === "/health") {
      return json({ ok: true, service: "aminekgogo-api" }, 200, request);
    }
    if (url.pathname === "/api/nearby") return handleNearby(url, request);
    if (url.pathname === "/api/geocode") return handleGeocode(url, request);
    return json({ error: "Not found" }, 404, request);
  },
};
