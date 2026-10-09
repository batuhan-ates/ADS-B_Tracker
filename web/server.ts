// server.ts
declare const Deno: any;

let latestPlanes: any[] = [];
let lastUpdate = 0;

Deno.serve(async (req: Request) => {
  const url = new URL(req.url);

  // 1. Python'dan canlı uçak verisini al (POST /api/update)
  if (req.method === "POST" && url.pathname === "/api/update") {
    try {
      latestPlanes = await req.json();
      lastUpdate = Date.now();
      return new Response(JSON.stringify({ status: "ok" }), {
        headers: { "Content-Type": "application/json" }
      });
    } catch {
      return new Response("Bad Request", { status: 400 });
    }
  }

  // 2. Tarayıcıdaki Leaflet haritasına veriyi ver (GET /data)
  if (url.pathname === "/data") {
    const planes = (Date.now() - lastUpdate < 30000) ? latestPlanes : [];
    return new Response(JSON.stringify(planes), {
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
      }
    });
  }

  // 3. Ana sayfada index.html'i sun (GET /)
  if (url.pathname === "/" || url.pathname === "/index.html") {
    try {
      // server.ts ile aynı klasördeki index.html'i kesin konumundan oku:
      const htmlUrl = new URL("./index.html", import.meta.url);
      const html = await Deno.readTextFile(htmlUrl);
      return new Response(html, {
        headers: { "Content-Type": "text/html; charset=utf-8" }
      });
    } catch (err) {
      return new Response("index.html okunamadı: " + err, { status: 500 });
    }
  }

  return new Response("Not Found", { status: 404 });
});