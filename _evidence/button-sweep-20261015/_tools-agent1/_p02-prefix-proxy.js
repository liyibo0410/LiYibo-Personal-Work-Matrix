/* 本地复刻公网 nginx 的「路径分流」：:18901/p02/* → 127.0.0.1:3001/*（剥前缀转发，
 * 浏览器地址栏仍保留 /p02/）。用于复现/验证「服务端 pathname 与浏览器 pathname 不一致」
 * 导致的水合告警（2.8），不依赖公网隧道。 */
const http = require('http');
const PORT = 18901;
const UP = { host: '127.0.0.1', port: 3001 };
const PREFIX = '/p02';

function strip(u) {
  if (u === PREFIX) return '/';
  if (u.startsWith(PREFIX + '/')) return u.slice(PREFIX.length);
  return u;
}

function fwdHeaders(req) {
  const h = { ...req.headers, host: '127.0.0.1:3001' };
  return h;
}

const server = http.createServer((req, res) => {
  const pre = http.request(
    { ...UP, path: strip(req.url), method: req.method, headers: fwdHeaders(req) },
    (r) => {
      res.writeHead(r.statusCode, r.headers);
      r.pipe(res);
    }
  );
  pre.on('error', (e) => {
    res.writeHead(502);
    res.end('prefix-proxy error: ' + e.message);
  });
  req.pipe(pre);
});

server.on('upgrade', (req, socket, head) => {
  const pre = http.request({ ...UP, path: strip(req.url), method: req.method, headers: fwdHeaders(req) });
  pre.on('upgrade', (r, s, h) => {
    let raw = 'HTTP/1.1 101 Switching Protocols\r\n';
    for (let i = 0; i < r.rawHeaders.length; i += 2) raw += r.rawHeaders[i] + ': ' + r.rawHeaders[i + 1] + '\r\n';
    raw += '\r\n';
    socket.write(raw);
    if (h && h.length) s.write(h);
    s.pipe(socket);
    socket.pipe(s);
  });
  pre.on('error', () => socket.destroy());
  if (head && head.length) pre.write(head);
  pre.end();
});

server.listen(PORT, () => console.log(`prefix-proxy :${PORT} -> ${UP.port} (strip ${PREFIX})`));
