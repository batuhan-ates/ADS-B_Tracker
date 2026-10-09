// web/server.ts
declare const Deno: any;

// Deno'nun ortak bulut hafızasını açıyoruz (tüm sunucular aynı hafızayı görür)
const kv = await Deno.openKv();

Deno.serve(async (req: Request) => {
  const url = new URL(req.url);

  // 1. Python'dan gelen uçakları ortak bulut hafızasına yaz (POST /api/update)
  if (req.method === "POST" && url.pathname === "/api/update") {
    try {
      const planes = await req.json();
      await kv.set(["planes"], planes);
      await kv.set(["lastUpdate"], Date.now());
      return new Response(JSON.stringify({ status: "ok" }), {
        headers: { "Content-Type": "application/json" }
      });
    } catch {
      return new Response("Bad Request", { status: 400 });
    }
  }

  // 2. Tarayıcıya ortak hafızadaki uçakları ver (GET /data)
  if (url.pathname === "/data") {
    const planesRes = await kv.get(["planes"]);
    const lastUpdateRes = await kv.get(["lastUpdate"]);

    const lastUpdate = (lastUpdateRes.value as number) || 0;
    // 30 saniyeden eskiyse boş döndür, yeniyse uçakları ver
    const planes = (Date.now() - lastUpdate < 30000) ? (planesRes.value || []) : [];

    return new Response(JSON.stringify(planes), {
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
      }
    });
  }

  // 3. index.html'i sun (GET /)
  if (url.pathname === "/" || url.pathname === "/index.html") {
    try {
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