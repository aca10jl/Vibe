#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_pptx.py — 生成《一键一生 × AI 伴读助手 方案》图解 PPT（精简版，16:9，含 Demo 实拍）
依赖：python-pptx>=1.0   运行：python3 make_pptx.py
截图：shots/*.png（由 shoot.mjs 用 Playwright 截取 Demo 页面生成）
输出：一键一生-AI助手-方案.pptx
"""
from pptx import Presentation
from pptx.util import Inches as In, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import os

BG     = RGBColor(0x0B, 0x12, 0x20)
PANEL  = RGBColor(0x14, 0x22, 0x38)
PANEL2 = RGBColor(0x0F, 0x18, 0x28)
LINE   = RGBColor(0x24, 0x3A, 0x52)
TEXT   = RGBColor(0xE6, 0xEE, 0xF7)
MUTED  = RGBColor(0x9F, 0xB3, 0xC8)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
ACC    = RGBColor(0x3B, 0x82, 0xF6)
ACC2   = RGBColor(0x1F, 0x9D, 0x55)
WARN   = RGBColor(0xF0, 0xA0, 0x20)
BAD    = RGBColor(0xE0, 0x53, 0x3D)
PUR    = RGBColor(0x7B, 0x2F, 0xF7)
FONT   = 'Microsoft YaHei'
NPAGES = 10
HERE   = os.path.dirname(os.path.abspath(__file__))
MID    = MSO_ANCHOR.MIDDLE

prs = Presentation()
prs.slide_width = In(13.333); prs.slide_height = In(7.5)
W, H = 13.333, 7.5
BLANK = prs.slide_layouts[6]

def slide():
    s = prs.slides.add_slide(BLANK); rect(s, 0, 0, W, H, BG); return s

def rect(s, x, y, w, h, fill, line=None, lw=1.0, rounded=False, radius=0.06):
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
                             In(x), In(y), In(w), In(h))
    shp.shadow.inherit = False
    if fill is None: shp.fill.background()
    else: shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line is None: shp.line.fill.background()
    else: shp.line.color.rgb = line; shp.line.width = Pt(lw)
    if rounded:
        try: shp.adjustments[0] = radius
        except Exception: pass
    return shp

def shp(s, mso, x, y, w, h, fill, line=None, lw=1.0):
    o = s.shapes.add_shape(mso, In(x), In(y), In(w), In(h)); o.shadow.inherit = False
    o.fill.solid(); o.fill.fore_color.rgb = fill
    if line is None: o.line.fill.background()
    else: o.line.color.rgb = line; o.line.width = Pt(lw)
    return o

def tb(s, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    box = s.shapes.add_textbox(In(x), In(y), In(w), In(h)); tf = box.text_frame
    tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = In(0.04); tf.margin_right = In(0.04); tf.margin_top = In(0.02); tf.margin_bottom = In(0.02)
    return tf

def para(tf, segs, size=14, color=TEXT, bold=False, align=PP_ALIGN.LEFT,
         first=False, space_after=4, space_before=0, bullet=False, lh=None):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align; p.space_after = Pt(space_after); p.space_before = Pt(space_before)
    if lh: p.line_spacing = lh
    if isinstance(segs, str): segs = [(segs, color, bold, size)]
    for seg in segs:
        t = seg[0]; col = seg[1] if len(seg) > 1 and seg[1] else color
        bd = seg[2] if len(seg) > 2 else bold
        sz = seg[3] if len(seg) > 3 and seg[3] else size
        r = p.add_run(); r.text = ('•  ' + t) if bullet else t
        r.font.size = Pt(sz); r.font.color.rgb = col; r.font.bold = bd; r.font.name = FONT
    return p

def head(s, kicker, title, idx=None):
    rect(s, 0, 0, W, 0.12, ACC)
    para(tb(s, 0.7, 0.42, 11.5, 0.4), kicker, size=12, color=ACC, bold=True, first=True)
    para(tb(s, 0.7, 0.74, 12.0, 0.7), title, size=26, color=WHITE, bold=True, first=True)
    rect(s, 0.72, 1.48, 1.15, 0.06, ACC2)
    para(tb(s, 0.7, 7.04, 8, 0.32), [('◧ 一键一生 × AI 伴读助手', MUTED, False, 10)], first=True)
    if idx is not None:
        para(tb(s, 11.6, 7.04, 1.1, 0.32), [(f'{idx:02d} / {NPAGES}', MUTED, False, 10)],
             align=PP_ALIGN.RIGHT, first=True)

def card(s, x, y, w, h, title, lines, accent=ACC, ticon=''):
    rect(s, x, y, w, h, PANEL, line=LINE, lw=1, rounded=True, radius=0.05)
    rect(s, x, y + 0.12, 0.07, h - 0.24, accent)
    tf = tb(s, x + 0.22, y + 0.14, w - 0.34, h - 0.28)
    if title:
        para(tf, [((ticon + ' ' if ticon else '') + title, WHITE, True, 14)], first=True, space_after=6)
    for i, ln in enumerate(lines):
        t, c = (ln[0], ln[1]) if isinstance(ln, tuple) else (ln, MUTED)
        para(tf, t, size=12, color=c, bullet=True, space_after=3, lh=1.05, first=(i == 0 and not title))

def fbox(s, x, y, w, h, title, sub='', fill=PANEL, line=ACC, tcol=WHITE, scol=MUTED, ts=13):
    rect(s, x, y, w, h, fill, line=line, lw=1.25, rounded=True, radius=0.08)
    tf = tb(s, x + 0.08, y, w - 0.16, h, anchor=MID)
    para(tf, [(title, tcol, True, ts)], align=PP_ALIGN.CENTER, first=True, space_after=2)
    if sub: para(tf, [(sub, scol, False, 10)], align=PP_ALIGN.CENTER, lh=1.0)

def note(s, x, y, w, h, title, body, accent):
    rect(s, x, y, w, h, PANEL, line=LINE, rounded=True, radius=0.08)
    rect(s, x, y + 0.1, 0.06, h - 0.2, accent)
    tf = tb(s, x + 0.18, y, w - 0.26, h, anchor=MID)
    para(tf, [(title, WHITE, True, 12.5)], first=True, space_after=2)
    para(tf, [(body, MUTED, False, 10.5)], lh=1.0)

def arrow(s, x, y, w, h, d='right', fill=ACC):
    m = {'right': MSO_SHAPE.RIGHT_ARROW, 'down': MSO_SHAPE.DOWN_ARROW,
         'left': MSO_SHAPE.LEFT_ARROW, 'up': MSO_SHAPE.UP_ARROW}[d]
    return shp(s, m, x, y, w, h, fill)

def table(s, x, y, w, h, data, col_w=None, hfill=ACC, fsz=11, hsz=12):
    rows, cols = len(data), len(data[0])
    g = s.shapes.add_table(rows, cols, In(x), In(y), In(w), In(h)).table
    g.first_row = False; g.horz_banding = False
    if col_w:
        for i, cw in enumerate(col_w): g.columns[i].width = In(cw)
    for r in range(rows):
        for c in range(cols):
            cell = g.cell(r, c); cell.fill.solid()
            cell.fill.fore_color.rgb = hfill if r == 0 else (PANEL if r % 2 else PANEL2)
            cell.vertical_anchor = MID
            cell.margin_left = In(0.1); cell.margin_right = In(0.06)
            cell.margin_top = In(0.03); cell.margin_bottom = In(0.03)
            val = data[r][c]; col = WHITE if r == 0 else TEXT
            if val.startswith('✓'): col = ACC2
            rr = cell.text_frame.paragraphs[0].add_run(); rr.text = val
            rr.font.size = Pt(hsz if r == 0 else fsz)
            rr.font.bold = (r == 0 or c == 0); rr.font.name = FONT
            rr.font.color.rgb = WHITE if (c == 0 and r > 0) else col

def chip(s, x, y, w, h, text, fill=PANEL, col=TEXT, line=LINE):
    rect(s, x, y, w, h, fill, line=line, lw=1, rounded=True, radius=0.5)
    para(tb(s, x, y, w, h, anchor=MID), [(text, col, True, 11)], align=PP_ALIGN.CENTER, first=True)

def picture(s, img, x, y, w):
    p = s.shapes.add_picture(os.path.join(HERE, img), In(x), In(y), width=In(w))
    p.line.color.rgb = LINE; p.line.width = Pt(1)
    return p

def demo_slide(kicker, title, idx, img, notes):
    s = slide(); head(s, kicker, title, idx)
    rect(s, 0.66, 1.74, 8.5, 5.32, PANEL2, line=LINE, rounded=True, radius=0.02)
    picture(s, img, 0.92, 1.9, 8.0)   # 8.0 宽 → 高约 5.08
    nx, ny, nw, nh, gap = 9.4, 1.95, 3.3, 1.14, 0.16
    para(tb(s, nx, 1.62, nw, 0.3), [('看点 Highlights', WARN, True, 12)], first=True)
    for i, (t, d, c) in enumerate(notes):
        note(s, nx, ny + i * (nh + gap), nw, nh, t, d, c)
    return s

# ============================================================ 1 封面
s = slide()
rect(s, 0, 0, W, 0.16, ACC); rect(s, 0, H - 0.1, W, 0.1, ACC2)
shp(s, MSO_SHAPE.OVAL, 10.3, -1.6, 4.5, 4.5, PANEL)
shp(s, MSO_SHAPE.OVAL, 11.2, 4.4, 3.6, 3.6, PANEL2)
para(tb(s, 0.9, 1.6, 9.5, 0.5), [('方案提案 · PROPOSAL', ACC, True, 14)], first=True)
tf = tb(s, 0.9, 2.1, 11.3, 2.0)
para(tf, [('一键一生 ', WHITE, True, 46), ('× ', ACC, True, 46), ('AI 伴读助手', ACC, True, 46)], first=True, space_after=6)
para(tf, [('让晶圆良率根因分析  会读 · 会想 · 会动手', TEXT, False, 22)])
para(tb(s, 0.9, 4.2, 11.4, 0.6),
     [('面向半导体 Wafer 全生命周期根因分析的智能体方案 —— 低侵入嵌入现有「一键一生」框架', MUTED, False, 14)], first=True)
for i, (t, c) in enumerate([('👁 伴读', ACC), ('🔍 分析', ACC2), ('💡 建议', WARN), ('🤖 会动手', PUR), ('🧠 学习习惯', ACC)]):
    chip(s, 0.9 + i * 1.78, 5.2, 1.62, 0.5, t, fill=PANEL, col=c)
para(tb(s, 0.9, 6.3, 11, 0.4),
     [('低风险 · 可私有化 · 即插即用 · 可成长 —— 内附可运行 Demo 实拍', MUTED, False, 12)], first=True)

# ============================================================ 2 痛点与机会
s = slide(); head(s, '01  背景与痛点', '一键一生很强，但"用好它"有门槛', 2)
para(tb(s, 0.7, 1.66, 12, 0.5),
     [('页面选项丰富、能一键还原晶圆全链路；但配置链路长、结果信息密度大，"会用、用对、读懂"高度依赖经验。', MUTED, False, 13)], first=True)
pains = [('配置门槛高', ['选项多、必填项易漏', '新手易错填，返工'], BAD, '⚠'),
         ('结果难解读', ['多图并列', '判读依赖资深工程师'], WARN, '📉'),
         ('经验依赖强', ['根因靠"老师傅"', '知识难标准化沉淀'], PUR, '🧓'),
         ('操作重复', ['常用配置反复手填', '习惯无法被记住'], ACC, '🔁')]
for i, (t, ls, c, ic) in enumerate(pains):
    card(s, 0.7 + i * 3.05, 2.3, 2.85, 1.95, t, ls, accent=c, ticon=ic)
rect(s, 0.7, 4.6, 11.93, 1.85, PANEL2, line=ACC2, lw=1.25, rounded=True, radius=0.04)
tf = tb(s, 1.0, 4.75, 11.4, 1.6, anchor=MID)
para(tf, [('机会 → 在页面右侧嵌入 AI 助手，恰好补齐这四块短板：', ACC2, True, 15)], first=True, space_after=8)
para(tf, [('伴读', ACC, True, 13), (' 降低解读门槛   ·   ', MUTED, False, 13),
          ('建议', ACC, True, 13), (' 保证正确提交   ·   ', MUTED, False, 13),
          ('分析', ACC, True, 13), (' 沉淀专家经验   ·   ', MUTED, False, 13),
          ('智能体', ACC, True, 13), (' 减少重复并持续学习习惯', MUTED, False, 13)])

# ============================================================ 3 方案总览
s = slide(); head(s, '02  方案总览', '一张图看懂：低侵入嵌入页面右侧', 3)
fbox(s, 0.7, 1.8, 3.7, 2.4, '左 · 配置区', '逐步向导\n①场景 ②维度 ③呈现 ④提交', line=ACC2, ts=15)
fbox(s, 4.7, 1.8, 4.3, 2.4, '中 · 结果呈现', '晶圆Bin图 · 良率/WAT趋势\n缺陷Pareto · 工艺时间轴 · 根因', line=ACC, ts=15)
fbox(s, 9.3, 1.8, 3.3, 2.4, '右 · AI 助手', '伴读 / 分析 / 建议\n对话 + 习惯画像', line=PUR, ts=15)
rect(s, 0.7, 4.55, 11.9, 1.5, PANEL, line=LINE, rounded=True, radius=0.04)
para(tb(s, 0.9, 4.64, 11.5, 0.4), [('Agent 引擎（纯前端，可嵌入任意页面）', WARN, True, 13)], first=True)
for i, (t, sub, c) in enumerate([('上下文采集', '读页面状态', ACC), ('工具调用', '真正改页面', ACC2),
                                  ('习惯学习', '沉淀画像', PUR), ('三来源 LLM', '规则/本地/Claude', WARN)]):
    fbox(s, 0.95 + i * 2.92, 5.08, 2.7, 0.82, t, sub, line=c, ts=12)
para(tb(s, 0.7, 6.2, 12, 0.5),
     [('嵌入方式：新增一个右侧 aside + 一组脚本，', MUTED, False, 12),
      ('不改动现有页面的提交与渲染逻辑', ACC2, True, 12),
      ('；AI 读取现有 DOM/状态作为上下文。', MUTED, False, 12)], first=True)

# ============================================================ 4 核心能力
s = slide(); head(s, '03  核心能力', '伴读 · 分析 · 建议 + 会动手 + 学习习惯', 4)
caps = [('👁 伴读', ACC, ['读懂页面与各面板含义', '提交后自动伴读']),
        ('🔍 分析', ACC2, ['commonality 根因打分', '候选 + 置信度排序']),
        ('💡 建议', WARN, ['校验填表→一键修正', '处置/下一步建议'])]
for i, (t, c, ls) in enumerate(caps):
    x = 0.7 + i * 4.05
    rect(s, x, 1.8, 3.8, 2.05, PANEL, line=c, lw=1.25, rounded=True, radius=0.05)
    para(tb(s, x + 0.25, 1.95, 3.4, 0.4), [(t, WHITE, True, 16)], first=True)
    tf = tb(s, x + 0.25, 2.45, 3.4, 1.3)
    for j, ln in enumerate(ls):
        para(tf, [(ln, TEXT, False, 12.5)], bullet=True, space_after=6, first=(j == 0))
rect(s, 0.7, 4.2, 5.85, 2.05, PANEL2, line=PUR, rounded=True, radius=0.04)
para(tb(s, 0.95, 4.35, 5.4, 0.4), [('🤖 智能体：会动手', PUR, True, 15)], first=True)
para(tb(s, 0.95, 4.85, 5.4, 1.3),
     [('通过工具调用真正操作页面：填表 / 设维度 / 提交 / 定位高亮面板。', TEXT, False, 12.5)], first=True, lh=1.15)
para(tb(s, 0.95, 5.55, 5.4, 0.6),
     [('不只是聊天框 —— 是能动手的智能体。', MUTED, False, 11.5)], first=True)
rect(s, 6.75, 4.2, 5.85, 2.05, PANEL2, line=ACC, rounded=True, radius=0.04)
para(tb(s, 7.0, 4.35, 5.4, 0.4), [('🧠 智能体：学习习惯', ACC, True, 15)], first=True)
para(tb(s, 7.0, 4.85, 5.4, 1.3),
     [('行为埋点 → 习惯画像（常用Fab/节点/维度）→ 个性化默认值与建议。', TEXT, False, 12.5)], first=True, lh=1.15)
para(tb(s, 7.0, 5.55, 5.4, 0.6), [('越用越懂你，新手→资深经验沉淀。', MUTED, False, 11.5)], first=True)

# ============================================================ 5/6/7 Demo 实拍
demo_slide('04  Demo 实拍（一）', '配置阶段：左侧逐步向导 + AI 全程伴读', 5, 'shots/01-config.png', [
    ('逐步向导', '①场景→②维度→③呈现→④提交，分步校验', ACC2),
    ('左配置 / 右 AI', '左侧专用配置，右侧助手伴读', PUR),
    ('AI 指引提交', '未就绪时一键修正必填项', WARN),
    ('零密钥可跑', '默认本地推理，开箱即用', ACC),
])
demo_slide('04  Demo 实拍（二）', '一键还原全链路 + AI 根因分析', 6, 'shots/04-ai-analyze.png', [
    ('全链路呈现', '晶圆图/良率/WAT/缺陷/工艺/根因', ACC),
    ('根因候选', 'commonality 打分：CMP-02 · 86%', ACC2),
    ('AI 分析', '自动高亮根因面板并给结论', WARN),
    ('结果阶段', '配置折叠为摘要，主区专注结果', PUR),
])
demo_slide('04  Demo 实拍（三）', '三种 AI 来源 · 私有化友好', 7, 'shots/05-ai-sources.png', [
    ('一键切换', '本地推理 / 本地大模型 / Claude', ACC),
    ('本地大模型', 'Ollama/vLLM/LM Studio，不出内网', ACC2),
    ('⚙ 即配', '前端填 Base URL/模型，连通测试', WARN),
    ('统一动手', '三来源都能操作页面', PUR),
])

# ============================================================ 8 集成方式 + 私有化
s = slide(); head(s, '05  集成方式', '低侵入接入现有框架（3 步）+ 私有化合规', 8)
steps = [('① 嵌入右侧栏', ACC, ['新增 aside + 脚本', '不改提交/渲染逻辑', '开关灰度']),
         ('② 适配上下文契约', ACC2, ['读现有 DOM/状态', '字段映射到快照', 'AI 看懂页面']),
         ('③ 注册页面工具', PUR, ['现有动作包装为', '白名单工具', 'AI 能动手'])]
for i, (t, c, ls) in enumerate(steps):
    x = 0.7 + i * 4.05
    card(s, x, 1.8, 3.8, 2.05, t, ls, accent=c)
    if i < 2: arrow(s, x + 3.82, 2.65, 0.32, 0.4, 'right', MUTED)
rect(s, 0.7, 4.1, 11.93, 1.5, PANEL2, line=ACC2, rounded=True, radius=0.03)
para(tb(s, 0.95, 4.2, 11.4, 0.4), [('数据契约：替换合成数据即接真实数据（可视化 + AI 复用，无需改动）', ACC2, True, 13)], first=True)
fbox(s, 0.95, 4.65, 3.4, 0.85, '真实 MES/YMS/EDA', '晶圆一生数据', fill=PANEL, line=ACC, ts=12)
arrow(s, 4.45, 4.92, 0.5, 0.32, 'right', MUTED)
fbox(s, 5.05, 4.65, 3.4, 0.85, 'generateLifecycle() 契约', 'meta/summary/waferMap/…', fill=PANEL, line=WARN, ts=12)
arrow(s, 8.55, 4.92, 0.5, 0.32, 'right', MUTED)
fbox(s, 9.15, 4.65, 3.4, 0.85, '可视化 + AI 复用', '无需改动', fill=PANEL, line=ACC2, ts=12)
para(tb(s, 0.7, 5.8, 12, 0.6),
     [('🔒 私有化/合规：', WARN, True, 13),
      ('本地大模型全程不出内网；密钥仅在后端；前端零密钥可跑；上下文只传必要派生摘要。', MUTED, False, 12.5)], first=True)

# ============================================================ 9 优势对比
s = slide(); head(s, '06  价值', '集成前 vs 集成后', 9)
data = [['环节', '集成前', '集成后（嵌入 AI 助手）'],
        ['任务提交', '必填易漏/错填，返工', '✓ 实时校验 + 一键修正再提交'],
        ['结果解读', '靠人工经验逐图判读', '✓ AI 伴读，逐面板讲解'],
        ['根因定位', '依赖资深工程师', '✓ 候选 + 置信度，秒级给出'],
        ['经验沉淀', '存于个人脑中', '✓ 习惯画像，可复用/可成长'],
        ['上手时间', '长，培训成本高', '✓ 显著缩短，新手即用'],
        ['数据合规', '—', '✓ 私有化 / 离线可选']]
table(s, 0.7, 1.85, 11.93, 4.25, data, col_w=[2.3, 4.6, 5.03], fsz=12.5, hsz=13)
para(tb(s, 0.7, 6.35, 12, 0.4),
     [('提交正确率 ↑   ·   解读门槛 ↓   ·   根因提速   ·   经验资产化   ·   合规可控', ACC2, True, 13.5)],
     first=True, align=PP_ALIGN.CENTER)

# ============================================================ 10 路线图 + CTA
s = slide(); head(s, '07  路线图与行动', '低风险灰度落地 · 我们的请求', 10)
phases = [('P0 · 1–2周', ACC, ['嵌入 + 本地推理', '对接数据契约']),
          ('P1 · 2–4周', ACC2, ['接本地大模型/Claude', '试点验证']),
          ('P2 · 进阶', WARN, ['流式输出', '跨会话记忆']),
          ('P3 · 增强', PUR, ['RAG: SOP/FA', '采纳信号学习'])]
for i, (t, c, ls) in enumerate(phases):
    x = 0.7 + i * 3.05
    rect(s, x, 1.8, 2.85, 0.45, c, rounded=True, radius=0.2)
    para(tb(s, x, 1.8, 2.85, 0.45, anchor=MID), [(t, WHITE, True, 12.5)], align=PP_ALIGN.CENTER, first=True)
    card(s, x, 2.35, 2.85, 1.5, '', ls, accent=c)
    if i < 3: arrow(s, x + 2.87, 1.9, 0.3, 0.28, 'right', MUTED)
card(s, 0.7, 4.25, 5.85, 2.15, '我们的请求', [
    ('批准 P0 灰度接入（约 2 周）', ACC2), ('指定 1 个试点产品线 / 页面', ACC2),
    ('明确数据合规边界', ACC2), ('指派 1 前端 + 1 数据对接', ACC2)], accent=ACC, ticon='✅')
card(s, 6.75, 4.25, 5.85, 2.15, '你将获得', [
    ('提交正确率与解读效率提升', WARN), ('根因提速、经验资产化', WARN),
    ('已可运行 Demo（本地零配置）', WARN), ('完整源码 + 设计 + 部署文档', WARN)], accent=ACC2, ticon='🎁')

out = os.path.join(HERE, '一键一生-AI助手-方案.pptx')
prs.save(out)
print('Saved:', out, '| slides:', len(prs.slides._sldIdLst))
