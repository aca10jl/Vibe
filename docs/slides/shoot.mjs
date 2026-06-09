/* shoot.mjs — 用 Playwright 截取 Demo 页面截图，供 PPT 使用 */
const _pw = await import(process.env.PW_PATH || 'playwright');
const chromium = _pw.chromium || (_pw.default && _pw.default.chromium);
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BASE = process.env.SHOT_URL || 'http://localhost:8799';
const OUT = path.join(__dirname, 'shots');

const sleep = ms => new Promise(r => setTimeout(r, ms));

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1480, height: 940 }, deviceScaleFactor: 2 });

async function shot(name) { await page.screenshot({ path: path.join(OUT, name) }); console.log('shot', name); }

await page.goto(BASE, { waitUntil: 'networkidle' });
await sleep(600);

// 1) 配置阶段（逐步向导，步骤1）
await shot('01-config.png');

// 走到步骤4，展示就绪度/摘要
for (let i = 0; i < 3; i++) { await page.click('#btnNext').catch(() => {}); await sleep(250); }
await sleep(300);
await shot('02-wizard-submit.png');

// 2) 一键示例 → 结果阶段 + AI 自动伴读
await page.click('#btnDemo');
await sleep(1800); // 等图表渲染 + AI 伴读气泡
await shot('03-result.png');

// 3) 点击 AI「分析」→ 根因分析 + 高亮根因面板
await page.click('#aiTabAnalyze');
await sleep(1500);
await shot('04-ai-analyze.png');

// 4) 切换 AI 来源下拉（展示三来源）+ 打开本地大模型设置
await page.selectOption('#aiMode', 'local').catch(() => {});
await page.click('#aiSettingsBtn').catch(() => {});
await sleep(500);
await shot('05-ai-sources.png');

await browser.close();
console.log('done');
