"""
生成网页地图编辑器（发布成 claude.ai Artifact，用来和 Claude 协同微调地形）。

读地图脚本里的地形、地貌、河流、资源、出生点和 选址规划.md 的关隘表，打包进一个 HTML 文件。
网页上改的格子存在 Artifact 的数据库（edits 集合，每格一条：x、y、t、f、bt、bf、note），
Claude 读出后用 tools/apply_edits.py 写回地图脚本，再重新生成、发布网页并清空已应用的改动。

用法：python tools/build_editor.py [地图脚本] [输出 HTML]
默认读 Zhanguo_V4/ZhanguoV4.lua，输出到 dist/editor/map_editor.html（已 gitignore）。
"""
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LUA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "Zhanguo_V4", "ZhanguoV4.lua")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "dist", "editor", "map_editor.html")
PLAN = os.path.join(os.path.dirname(os.path.abspath(LUA)), "选址规划.md")
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "editor_template.html")

src = open(LUA, encoding="utf-8").read()
blk = lambda n: re.search(r"local " + n + r" = \{(.*?)\r?\n\}", src, re.S).group(1)
T = re.findall(r'"([^"]+)"', blk("TERRAIN_ROWS"))
F = re.findall(r'"([^"]+)"', blk("FEATURE_ROWS"))
ver = re.search(r"Warring States China map (V[\d.]+)", src) or re.search(r"(V\d+\.\d+)", src)

res = {}
for name in ("SITE_RESOURCES", "GUAR_RESOURCES", "SCATTER_RESOURCES"):
    for x, y, r in re.findall(r'x = (\d+), y = (\d+), res = "(\w+)"', blk(name)):
        res.setdefault(f"{x},{y}", r)

starts = [[n, int(x), int(y)] for n, x, y in re.findall(r'name = "(\w+)", x = (\d+), y = (\d+)', blk("START_POSITIONS"))]
rivers = [list(map(int, m)) for m in re.findall(r"\{ (\d+), (\d+), (\d+), (\d+) \}", blk("RIVER_PAIRS"))]
yellow = [[int(x), int(y)] for x, y in re.findall(r"x = (\d+), y = (\d+)", blk("YELLOW_EDGE_CELLS"))]

passes = []
if os.path.exists(PLAN):
    part = open(PLAN, encoding="utf-8").read().split("## 关隘坐标", 1)
    if len(part) == 2:
        for _, n, x, y in re.findall(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*\((\d+),\s*(\d+)\)\s*\|", part[1]):
            passes.append([re.sub(r"[（(].*?[）)]", "", n), int(x), int(y)])

data = {
    "ver": ver.group(1) if ver else "",
    "base": hashlib.sha1(("".join(T) + "".join(F)).encode()).hexdigest()[:10],
    "W": len(T[0]), "H": len(T), "T": T, "F": F,
    "res": res, "starts": starts, "rivers": rivers, "yellow": yellow, "passes": passes,
}
html = open(TEMPLATE, encoding="utf-8").read().replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(html)
print(f"{OUT}  {data['ver']}  底图 {data['base']}  {len(html) // 1024} KB")
