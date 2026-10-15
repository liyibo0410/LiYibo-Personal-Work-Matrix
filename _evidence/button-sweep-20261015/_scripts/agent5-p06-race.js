/* P06 竞态复现实验（只读）
 * 对每张表并发调用 GET /tables/{name} 与 /tables/{name}/preview?limit=5（与前端 showTableDetail 的 Promise.all 相同）
 * 统计「preview 200 但 info 404」的矛盾配对数；再做一组串行对照。
 * env: P06_BASE 默认 http://127.0.0.1:8060
 */
const base = process.env.P06_BASE || 'http://127.0.0.1:8060';
const tables = ['ads_key_metrics', 'ads_product_ranking', 'dwd_customer_profile', 'dwd_order_detail', 'dws_daily_shop', 'ods_products', 'ods_stores', 'ods_traffic', 'ods_orders'];
const N = Number(process.env.N || 12);

(async () => {
  const out = { base, ts: new Date().toISOString(), rounds: N, parallel: [], serial: [], contradictions: 0 };
  for (let r = 0; r < N; r++) {
    const t = tables[r % tables.length];
    const [a, b] = await Promise.all([
      fetch(`${base}/api/v1/tables/${t}`).then(async x => ({ s: x.status, m: (await x.json().catch(() => ({}))).msg })),
      fetch(`${base}/api/v1/tables/${t}/preview?limit=5`).then(async x => ({ s: x.status })),
    ]);
    const rec = { round: r + 1, table: t, info: a.s, infoMsg: a.m, preview: b.s };
    if (b.s === 200 && a.s === 404) { rec.contradiction = true; out.contradictions++; }
    out.parallel.push(rec);
    process.stdout.write(`P${r + 1} ${t} info=${a.s} preview=${b.s}${rec.contradiction ? '  <<< 矛盾' : ''}\n`);
  }
  // 串行对照：完全相同的请求序列，但一次只发一个
  for (let r = 0; r < N; r++) {
    const t = tables[r % tables.length];
    const a = await fetch(`${base}/api/v1/tables/${t}`).then(x => x.status);
    const b = await fetch(`${base}/api/v1/tables/${t}/preview?limit=5`).then(x => x.status);
    out.serial.push({ round: r + 1, table: t, info: a, preview: b });
    process.stdout.write(`S${r + 1} ${t} info=${a} preview=${b}\n`);
  }
  const fs = require('fs');
  const OUT = process.env.RACE_OUT || 'D:/software/PycharmProjects/作品矩阵/_evidence/button-sweep-20261015/agent5-p06-race-experiment.json';
  fs.writeFileSync(OUT, JSON.stringify(out, null, 2), 'utf-8');
  console.log('contradictions(parallel)=', out.contradictions, '/', N);
  console.log('serial-any-404=', out.serial.filter(x => x.info !== 200 || x.preview !== 200).length);
})();