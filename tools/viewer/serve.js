// tools/viewer を http://localhost:8765/ で配信するだけの小さなサーバ（外部パッケージなし）。
// 使い方: node tools/viewer/serve.js   → ブラウザで http://localhost:8765/ （一覧）
// /design/〜 はリポジトリの design フォルダの文書（.md など）を読むだけに使う（diagram.html で Mermaid を描くため）。
const http = require("http");
const fs = require("fs");
const path = require("path");

const ROOT = __dirname;
const DESIGN = path.join(__dirname, "..", "..", "design");
const PORT = Number(process.env.PORT) || 8765;
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
                ".md": "text/markdown; charset=utf-8" };

http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (p === "/") p = "/index.html";
  const [base, rel] = p.startsWith("/design/") ? [DESIGN, p.slice("/design".length)] : [ROOT, p];
  const file = path.join(base, path.normalize(rel));
  if (!file.startsWith(base)) { res.writeHead(403); return res.end(); }
  fs.readFile(file, (err, data) => {
    if (err) { res.writeHead(404); return res.end("not found"); }
    res.writeHead(200, { "Content-Type": TYPES[path.extname(file)] || "application/octet-stream" });
    res.end(data);
  });
}).listen(PORT, "127.0.0.1", () => console.log(`viewer: http://localhost:${PORT}/`));
