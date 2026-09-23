import zlib from 'node:zlib';

const BASE = 'https://ai.tju.edu.cn/api/v3';
const KEY = process.env.TJU_LLM_API_KEY;
const H = { 'Content-Type': 'application/json', Authorization: `Bearer ${KEY}` };

function crc32(buf){let c,crc=0xffffffff;for(let n=0;n<buf.length;n++){c=(crc^buf[n])&0xff;for(let k=0;k<8;k++)c=c&1?0xedb88320^(c>>>1):c>>>1;crc=c^(crc>>>8);}return (crc^0xffffffff)>>>0;}
function chunk(t,d){const l=Buffer.alloc(4);l.writeUInt32BE(d.length);const td=Buffer.concat([Buffer.from(t,'ascii'),d]);const c=Buffer.alloc(4);c.writeUInt32BE(crc32(td));return Buffer.concat([l,td,c]);}
function solid(w,h,[r,g,b]){const ih=Buffer.alloc(13);ih.writeUInt32BE(w,0);ih.writeUInt32BE(h,4);ih[8]=8;ih[9]=2;const raw=Buffer.alloc(h*(1+w*3));for(let y=0;y<h;y++){const o=y*(1+w*3);raw[o]=0;for(let x=0;x<w;x++){raw[o+1+x*3]=r;raw[o+2+x*3]=g;raw[o+3+x*3]=b;}}return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',ih),chunk('IDAT',zlib.deflateSync(raw)),chunk('IEND',Buffer.alloc(0))]).toString('base64');}

async function test(label, body) {
  const t0 = Date.now();
  const r = await fetch(BASE + '/chat/completions', { method: 'POST', headers: H, body: JSON.stringify(body) });
  const ms = Date.now() - t0;
  const j = await r.json();
  const m = j.choices?.[0]?.message || {};
  console.log(`${label} [${r.status}] ${ms}ms | reasoning=${(m.reasoning||'').length} | content=${(m.content||'').length} | ${JSON.stringify((m.content||'').slice(0,100))}`);
}

// 纯红图
const red = solid(96, 96, [220, 20, 20]);
await test('纯红图 (无思考)', {
  model: 'qwen3.6-35b-a3b', max_tokens: 50,
  messages: [{ role: 'user', content: [
    { type: 'text', text: '这张图的主色是什么？一个词。' },
    { type: 'image_url', image_url: { url: 'data:image/png;base64,' + red } },
  ]}],
});

// 纯绿图
const green = solid(96, 96, [20, 200, 40]);
await test('纯绿图 (无思考)', {
  model: 'qwen3.6-35b-a3b', max_tokens: 50,
  messages: [{ role: 'user', content: [
    { type: 'text', text: '这张图的主色是什么？一个词。' },
    { type: 'image_url', image_url: { url: 'data:image/png;base64,' + green } },
  ]}],
});

// 红图 + 思考
await test('纯红图 (有思考)', {
  model: 'qwen3.6-35b-a3b', max_tokens: 500,
  chat_template_kwargs: { enable_thinking: true, preserve_thinking: true },
  thinking_token_budget: 512,
  messages: [{ role: 'user', content: [
    { type: 'text', text: '这张图的主色是什么？一个词。' },
    { type: 'image_url', image_url: { url: 'data:image/png;base64,' + red } },
  ]}],
});

// 蓝图
const blue = solid(96, 96, [30, 40, 220]);
await test('纯蓝图 (有思考)', {
  model: 'qwen3.6-35b-a3b', max_tokens: 500,
  chat_template_kwargs: { enable_thinking: true, preserve_thinking: true },
  thinking_token_budget: 512,
  messages: [{ role: 'user', content: [
    { type: 'text', text: '这张图的主色是什么？一个词。' },
    { type: 'image_url', image_url: { url: 'data:image/png;base64,' + blue } },
  ]}],
});
