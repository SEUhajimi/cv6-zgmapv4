"""
把战国七雄地图（Zhanguo_V4/ZhanguoV4.lua）画成 PNG：一张全图、七张分区放大图和一张关隘标注图。

读取地图脚本里的地形、地貌、出生点、淡水河边（RIVER_PAIRS、YELLOW_EDGE_CELLS）和悬崖（CLIFF_CELLS），
按游戏的六边形排布（奇数行右移半格）绘制。改了地形后重新运行，预览图就和游戏里生成的地图一致。
关隘标注图（08_关隘.png）的位置取自 Zhanguo_V4/选址规划.md 末尾的“关隘坐标”表（和地图脚本同目录），只作参考，游戏数据里没有关隘。

用法：python tools/render_map.py [地图脚本] [输出目录]
默认读 Zhanguo_V4/ZhanguoV4.lua，输出到 Zhanguo_V4/地图预览/。需要 Pillow 和 Windows 自带的微软雅黑字体。
"""
import math
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LUA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "Zhanguo_V4", "ZhanguoV4.lua")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "Zhanguo_V4", "地图预览")
PLAN = os.path.join(os.path.dirname(os.path.abspath(LUA)), "选址规划.md")
src = open(LUA, encoding="utf-8").read()


def block(name):
    return re.search(r"local " + name + r" = \{(.*?)\r?\n\}", src, re.S).group(1)


T = re.findall(r'"([^"]+)"', block("TERRAIN_ROWS"))
F = re.findall(r'"([^"]+)"', block("FEATURE_ROWS"))
H, W = len(T), len(T[0])
terr = lambda x, y: T[H - 1 - y][x]
feat = lambda x, y: F[H - 1 - y][x]
starts = [(n, int(x), int(y)) for n, x, y in re.findall(r'name = "(\w+)", x = (\d+), y = (\d+)', src.split("local LEADER_BIND")[0])]
river_pairs = [tuple(map(int, m)) for m in re.findall(r"\{ (\d+), (\d+), (\d+), (\d+) \}", block("RIVER_PAIRS"))]
yellow = [(int(x), int(y)) for x, y in re.findall(r"x = (\d+), y = (\d+)", block("YELLOW_EDGE_CELLS"))]
cliffs = [(int(x), int(y)) for x, y in re.findall(r"x = (\d+), y = (\d+)", block("CLIFF_CELLS"))]

CN = {
    "Handan": "邯郸", "Jinyang": "晋阳", "Xianyang": "咸阳", "Luoyang": "洛阳", "Xiangyang": "襄阳",
    "Chengdu": "成都", "Hefei": "合肥", "Anyi": "安邑", "Ji": "蓟", "Linzi": "临淄", "Xuzhou": "徐州",
    "Chongqing": "江州", "Nanjing": "南京", "Kuaiji": "会稽", "Hanzhong": "汉中", "Jiangling": "江陵",
    "Daliang": "大梁", "Zhongshan": "中山", "Wuchang": "武昌",
}
COLOR = {
    "~": (36, 72, 128), "c": (92, 150, 205),
    "g": (120, 170, 80), "p": (196, 190, 110), "d": (228, 206, 150),
    "G": (88, 132, 58), "P": (160, 150, 82), "D": (196, 168, 110),
    "M": (120, 104, 92), "S": (232, 236, 240),
}
FEAT_COLOR = {"f": (40, 92, 40), "j": (20, 120, 70), "m": (70, 110, 120)}
RIVER = (60, 130, 230)
CLIFF = (90, 40, 30)


def neighbors(x, y):
    # 奇数行右移半格（游戏的排布），方向顺序：东、西、东北、西北、东南、西南
    if y & 1:
        d = {"E": (1, 0), "W": (-1, 0), "NE": (1, 1), "NW": (0, 1), "SE": (1, -1), "SW": (0, -1)}
    else:
        d = {"E": (1, 0), "W": (-1, 0), "NE": (0, 1), "NW": (-1, 1), "SE": (0, -1), "SW": (-1, -1)}
    return {k: (x + dx, y + dy) for k, (dx, dy) in d.items()}


def render(path, x0, x1, y0, y1, R, title, overlay=None):
    sq = math.sqrt(3)
    margin = int(R * 2.5)
    top = int(R * 3.2)  # 标题栏

    def center(x, y):
        cx = margin + R * sq * ((x - x0) + 0.5 * (y & 1)) + R * sq / 2
        cy = top + margin + R * 1.5 * (y1 - y) + R
        return cx, cy

    def corners(x, y):
        cx, cy = center(x, y)
        return [(cx + R * math.cos(math.radians(60 * i - 30)), cy + R * math.sin(math.radians(60 * i - 30))) for i in range(6)]

    width = int(margin * 2 + R * sq * (x1 - x0 + 1.5))
    height = int(top + margin * 2 + R * 1.5 * (y1 - y0) + R * 2)
    img = Image.new("RGB", (width, height), (24, 28, 36))
    dr = ImageDraw.Draw(img)
    font_t = ImageFont.truetype("msyhbd.ttc", max(16, int(R * 1.5)))
    font_l = ImageFont.truetype("msyhbd.ttc", max(13, int(R * 1.15)))
    font_s = ImageFont.truetype("msyh.ttc", max(10, int(R * 0.6)))

    cells = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if 0 <= x < W and 0 <= y < H]
    for x, y in cells:
        t = terr(x, y)
        dr.polygon(corners(x, y), fill=COLOR[t], outline=(0, 0, 0) if R >= 14 else None)
        cx, cy = center(x, y)
        if t in "MS":  # 山峰
            c = (80, 70, 62) if t == "M" else (170, 176, 186)
            dr.polygon([(cx - R * .55, cy + R * .4), (cx, cy - R * .55), (cx + R * .55, cy + R * .4)], fill=c)
        elif t in "GPD":  # 丘陵
            dr.arc([cx - R * .5, cy - R * .25, cx + R * .5, cy + R * .55], 200, 340, fill=(50, 50, 30), width=max(1, R // 8))
        f = feat(x, y)
        if f in FEAT_COLOR:
            rr = R * .18
            for ox, oy in ((-.35, .1), (.3, .2), (0, -.3)):
                dr.ellipse([cx + ox * R - rr, cy + oy * R - rr, cx + ox * R + rr, cy + oy * R + rr], fill=FEAT_COLOR[f])

    inside = lambda c: x0 <= c[0] <= x1 and y0 <= c[1] <= y1

    def edge(a, b, color, wdt):
        if not (inside(a) and inside(b)):
            return
        ca, cb = corners(*a), corners(*b)
        shared = [p for p in ca if any(abs(p[0] - q[0]) < 1 and abs(p[1] - q[1]) < 1 for q in cb)]
        if len(shared) == 2:
            dr.line(shared, fill=color, width=wdt)

    rw = max(2, R // 4)
    for x, y, x2, y2 in river_pairs:
        if inside((x, y)):
            edge((x, y), (x2, y2), RIVER, rw)
    for x, y in yellow:
        if inside((x, y)):
            n = neighbors(x, y)
            edge((x, y), n["SE"], RIVER, rw)
            edge((x, y), n["SW"], RIVER, rw)
    for x, y in cliffs:
        if inside((x, y)):
            for nb in neighbors(x, y).values():
                if 0 <= nb[0] < W and 0 <= nb[1] < H and terr(*nb) in "~c":
                    edge((x, y), nb, CLIFF, max(2, R // 3))

    # 放大图每 5 格标一次坐标
    if R >= 14:
        for x in range(x0, x1 + 1):
            if x % 5 == 0:
                cx, _ = center(x, y1)
                dr.text((cx, top + margin * .35), str(x), font=font_s, fill=(170, 170, 170), anchor="mm")
        for y in range(y0, y1 + 1):
            if y % 5 == 0:
                _, cy = center(x0, y)
                dr.text((margin * .45, cy), str(y), font=font_s, fill=(170, 170, 170), anchor="mm")

    for n, x, y in starts:
        if x0 <= x <= x1 and y0 <= y <= y1:
            cx, cy = center(x, y)
            r = R * .55
            star = [(cx + (r if i % 2 == 0 else r * .45) * math.cos(math.radians(90 + 36 * i)),
                     cy - (r if i % 2 == 0 else r * .45) * math.sin(math.radians(90 + 36 * i))) for i in range(10)]
            dr.polygon(star, fill=(230, 40, 40), outline=(255, 255, 255))
            label = CN.get(n, n)
            dr.text((cx, cy - R * 1.25), label, font=font_l, fill=(255, 255, 255), anchor="ms",
                    stroke_width=max(2, R // 6), stroke_fill=(0, 0, 0))

    dr.text((margin, top * .5), title, font=font_t, fill=(240, 230, 200), anchor="lm")
    # 图例
    items = [("草原", COLOR["g"]), ("平原", COLOR["p"]), ("沙漠", COLOR["d"]), ("丘陵", COLOR["G"]), ("山地", COLOR["M"]),
             ("雪山", COLOR["S"]), ("江河/近海", COLOR["c"]), ("外海", COLOR["~"]), ("森林", FEAT_COLOR["f"]),
             ("河边(淡水)", RIVER), ("悬崖", CLIFF), ("出生点", (230, 40, 40))]
    lx = width - margin
    for name, c in reversed(items):
        tw = dr.textlength(name, font=font_s)
        lx -= tw
        dr.text((lx, top * .5), name, font=font_s, fill=(220, 220, 220), anchor="lm")
        lx -= font_s.size * 1.1
        dr.rectangle([lx, top * .5 - font_s.size * .4, lx + font_s.size * .8, top * .5 + font_s.size * .4], fill=c)
        lx -= font_s.size * .9
    if overlay:
        overlay(dr, center, R)
    img.save(path)
    print(path, img.size)


def read_passes():
    """读 选址规划.md 里“关隘坐标”表的每一行：(名称, x, y)，名称去掉括号里的别名。"""
    text = open(PLAN, encoding="utf-8").read()
    part = text.split("## 关隘坐标", 1)
    if len(part) < 2:
        return []
    rows = re.findall(r"^\| [^|]+ \| ([^|]+?) \| \((\d+), (\d+)\) \|", part[1], re.M)
    return [(re.sub(r"（.*?）|\(.*?\)", "", n).strip(), int(x), int(y)) for n, x, y in rows]


def draw_passes(passes):
    def overlay(dr, center, R):
        font = ImageFont.truetype("msyhbd.ttc", int(R * 0.95))
        # 出生点标签已画在上方，关隘标签依次试上、下、右、左，避开已放的标签
        placed = []
        for _, x, y in starts:
            cx, cy = center(x, y)
            placed.append((cx - R * 1.2, cy - R * 2.4, cx + R * 1.2, cy - R * 1.0))

        def box(cx, cy, w, h, pos):
            if pos == "up":
                return (cx - w / 2, cy - R * 1.0 - h, cx + w / 2, cy - R * 1.0)
            if pos == "down":
                return (cx - w / 2, cy + R * 1.0, cx + w / 2, cy + R * 1.0 + h)
            if pos == "right":
                return (cx + R * 0.9, cy - h / 2, cx + R * 0.9 + w, cy + h / 2)
            return (cx - R * 0.9 - w, cy - h / 2, cx - R * 0.9, cy + h / 2)

        hit = lambda a, b: not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])
        for _, x, y in passes:
            cx, cy = center(x, y)
            r = R * 0.5
            dr.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=(255, 200, 40), outline=(0, 0, 0))
        for name, x, y in passes:
            cx, cy = center(x, y)
            tw, th = dr.textlength(name, font=font), font.size * 1.1
            for pos in ("up", "down", "right", "left"):
                b = box(cx, cy, tw, th, pos)
                if not any(hit(b, q) for q in placed):
                    break
            placed.append(b)
            dr.text(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), name, font=font, fill=(255, 215, 90), anchor="mm",
                    stroke_width=3, stroke_fill=(0, 0, 0))
    return overlay


# 分区范围按 V3（106×66）写的，其他尺寸的地图按比例换算
REGIONS_V3 = [
    ("01_关中汉中.png", 20, 50, 20, 42, "关中 · 汉中 · 河东（咸阳 安邑 汉中）"),
    ("02_巴蜀.png", 0, 34, 2, 30, "巴蜀（成都 江州）"),
    ("03_中原.png", 44, 76, 24, 42, "中原（洛阳 安邑 大梁）"),
    ("04_燕赵.png", 48, 88, 38, 65, "燕赵 · 中山（晋阳 邯郸 中山 蓟）"),
    ("05_齐鲁徐州.png", 66, 105, 26, 52, "齐鲁 · 徐州（临淄 徐州）"),
    ("06_荆楚.png", 34, 72, 2, 30, "荆楚（襄阳 武昌）"),
    ("07_江淮吴越.png", 66, 105, 0, 30, "江淮 · 吴越（合肥 南京 会稽 武昌）"),
]
REGIONS = [(fn, round(a * W / 106), min(W - 1, round(b * W / 106)), round(c * H / 66), min(H - 1, round(d * H / 66)), t)
           for fn, a, b, c, d, t in REGIONS_V3]
VER = (re.search(r"Warring States China\s+(V\d+)", src) or re.search(r"(V\d+)", "V3")).group(1)


def main():
    os.makedirs(OUT, exist_ok=True)
    render(os.path.join(OUT, "00_全图.png"), 0, W - 1, 0, H - 1, 11, f"战国七雄 {VER} · 全图（{W}×{H}，上北下南）")
    for fn, a, b, c, d, title in REGIONS:
        render(os.path.join(OUT, fn), a, b, c, d, 24, title)
    passes = read_passes()
    if passes:
        render(os.path.join(OUT, "08_关隘.png"), 0, W - 1, 0, H - 1, 15, f"战国七雄 {VER} · 关隘位置（仅作参考，未写入游戏数据）",
               draw_passes(passes))


if __name__ == "__main__":
    main()
