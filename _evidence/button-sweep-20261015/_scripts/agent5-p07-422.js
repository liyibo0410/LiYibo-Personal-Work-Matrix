/* P07 后端 422 拒绝验证 + 清理（只读探针 + 临时资产）
 * 1) 上传「UI测试-可删-422探针」（auto_tag=false，快）
 * 2) POST 非法投放（clicks 900 > impressions 100）→ 期望 422
 * 3) 删除临时资产
 */
const fs = require('fs');
const B = process.env.P07_API || 'http://127.0.0.1:8070/api/v1';
const SRC = 'D:\\software\\PycharmProjects\\作品矩阵\\projects\\p07-ai-asset-center\\data\\uploads\\AST-18356A.png';

(async () => {
  const out = {};
  const form = new FormData();
  form.append('name', 'UI测试-可删-422探针');
  form.append('asset_type', 'image');
  form.append('tags', 'UI测试');
  form.append('description', 'UI测试临时探针（可删）');
  form.append('auto_tag', 'false');
  form.append('file', new Blob([fs.readFileSync(SRC)], { type: 'image/png' }), 'probe.png');
  const up = await fetch(`${B}/assets`, { method: 'POST', body: form });
  const upBody = await up.json();
  out.upload = { status: up.status, id: upBody.asset_id, tag_source: upBody.tagging && upBody.tagging.tag_source };
  console.log('upload', JSON.stringify(out.upload));

  const bad = await fetch(`${B}/assets/${out.upload.id}/performance`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ store_name: 'UI测试-可删门店', platform: 'douyin', impressions: 100, clicks: 900, conversions: 10, spend: 10, revenue: 20, period_start: '2026-10-01', period_end: '2026-10-13' })
  });
  out.invalidPerf = { status: bad.status, body: JSON.stringify(await bad.json().catch(() => null)).slice(0, 400) };
  console.log('invalid-perf', JSON.stringify(out.invalidPerf));

  const del = await fetch(`${B}/assets/${out.upload.id}`, { method: 'DELETE' });
  out.cleanup = { status: del.status, body: JSON.stringify(await del.json().catch(() => null)).slice(0, 200) };
  console.log('cleanup', JSON.stringify(out.cleanup));

  fs.writeFileSync('D:/software/PycharmProjects/作品矩阵/_evidence/button-sweep-20261015/agent5-p07-422-probe.json', JSON.stringify({ ts: new Date().toISOString(), base: B, out }, null, 2), 'utf-8');
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });