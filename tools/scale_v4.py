"""
把战国七雄 V3（巨型 106×66）等比缩小成 V4（标准 84×54）。

读旁边 mapzg-cv6 仓库的 Zhanguo_V3/ZhanguoV3.lua，把地形、地貌和所有带坐标的数据缩放后写进 Zhanguo_V4/ZhanguoV4.lua
（只替换数据块，GenerateMap 等代码不动），同时缩放 ZhanguoV4_Gameplay.lua 的城址和蛮族区、
选址规划.md 的关隘坐标表。

缩放方法：每个 V3 格子按六边形中心的真实位置缩放，落到最近的 V4 格子上。一个 V4 格子收到多个 V3 格子时：
  水面 > 山地 > 陆地。
水面优先，大河不会被缩断；山地优先，山脉不会被缩出缺口。这样窄的河谷、关口和浅滩会被盖住，
之后逐对比较抽样点之间的陆路距离，被堵死或绕远的，沿 V3 原来的路在 V4 里挖开（只挖开 V3 里本来
就相邻的陆地之间的山或水，不会造出捷径）。没有收到任何 V3 格子的 V4 格子取最近的 V3 格子。
陆地之间按多数取地形，地貌取同一个来源格。缩放后的手工修正写在 FIXES 里，每次运行都会重新应用。

这是一次性的转换工具：V4 定稿后以 ZhanguoV4.lua 为准，再运行会覆盖 V4 里手工改过的数据块。
用法：python tools/scale_v4.py [--check]   --check 只做检查不写文件。
"""
import collections
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V3_DIR = os.path.join(os.path.dirname(ROOT), "mapzg-cv6", "Zhanguo_V3")  # V3 在旁边的 mapzg-cv6 仓库
V3 = os.path.join(V3_DIR, "ZhanguoV3.lua")
V4 = os.path.join(ROOT, "Zhanguo_V4", "ZhanguoV4.lua")
V4_GAMEPLAY = os.path.join(ROOT, "Zhanguo_V4", "ZhanguoV4_Gameplay.lua")
V4_PLAN = os.path.join(ROOT, "Zhanguo_V4", "选址规划.md")
CHECK = "--check" in sys.argv

W2, H2 = 84, 54

# 缩放后的手工修正：(x, y) -> 地形字符（V4 坐标）
FIXES = {
}

src = open(V3, encoding="utf-8", newline="").read()


def block(text, name):
    return re.search(r"local " + name + r" = \{(.*?)\r?\n\}", text, re.S)


T = re.findall(r'"([^"]+)"', block(src, "TERRAIN_ROWS").group(1))
F = re.findall(r'"([^"]+)"', block(src, "FEATURE_ROWS").group(1))
H1, W1 = len(T), len(T[0])
t1 = lambda x, y: T[H1 - 1 - y][x]
f1 = lambda x, y: F[H1 - 1 - y][x]
KX, KY = W2 / W1, H2 / H1
SQ = math.sqrt(3) / 2


def nbrs(x, y, W, H):
    d = [(1, 0), (-1, 0), (0, 1), (1, 1), (0, -1), (1, -1)] if y & 1 else [(1, 0), (-1, 0), (-1, 1), (0, 1), (-1, -1), (0, -1)]
    for dx, dy in d:
        nx, ny = x + dx, y + dy
        if 0 <= nx < W and 0 <= ny < H:
            yield nx, ny


def center(x, y):
    return x + 0.5 * (y & 1), y * SQ


def to_v4(x, y):
    """V3 坐标 -> 最近的 V4 格子"""
    cx, cy = center(x, y)
    rx, ry = cx * KX, (y * KY) * SQ
    best = None
    for Y in (math.floor(y * KY), math.ceil(y * KY)):
        Y = min(max(Y, 0), H2 - 1)
        for X in (math.floor(rx - 0.5 * (Y & 1)), math.ceil(rx - 0.5 * (Y & 1))):
            X = min(max(X, 0), W2 - 1)
            ax, ay = center(X, Y)
            d = (ax - rx) ** 2 + (ay - ry) ** 2
            if best is None or d < best[0]:
                best = (d, X, Y)
    return best[1], best[2]


def to_v3(X, Y):
    """V4 格子 -> 最近的 V3 格子"""
    ax, ay = center(X, Y)
    rx, y = ax / KX, Y / KY
    best = None
    for yy in (math.floor(y), math.ceil(y)):
        yy = min(max(yy, 0), H1 - 1)
        for xx in (math.floor(rx - 0.5 * (yy & 1)), math.ceil(rx - 0.5 * (yy & 1))):
            xx = min(max(xx, 0), W1 - 1)
            cx, cy = center(xx, yy)
            d = (cx - rx) ** 2 + (cy - y * SQ) ** 2
            if best is None or d < best[0]:
                best = (d, xx, yy)
    return best[1], best[2]


WATER, MTN = "~c", "MS"
land1 = lambda x, y: t1(x, y) not in WATER + MTN


def bfs(passable, starts, W, H, limit=10 ** 9):
    D = {s: 0 for s in starts}
    q = collections.deque(starts)
    while q:
        u = q.popleft()
        if D[u] >= limit:
            continue
        for v in nbrs(*u, W, H):
            if v not in D and passable(*v):
                D[v] = D[u] + 1
                q.append(v)
    return D


# ---- 地形 ----
recv = collections.defaultdict(list)
for y in range(H1):
    for x in range(W1):
        recv[to_v4(x, y)].append((x, y))

T2 = [[None] * W2 for _ in range(H2)]
F2 = [["."] * W2 for _ in range(H2)]
for Y in range(H2):
    for X in range(W2):
        S = recv.get((X, Y)) or [to_v3(X, Y)]
        ax, ay = center(X, Y)
        near = lambda c: (center(*c)[0] * KX - ax) ** 2 + (c[1] * KY * SQ - ay) ** 2
        S = sorted(S, key=near)
        water = [c for c in S if t1(*c) in WATER]
        mtn = [c for c in S if t1(*c) in MTN]
        lnd = [c for c in S if land1(*c)]
        if water:
            ch = "~" if sum(t1(*c) == "~" for c in water) * 2 > len(water) else "c"
            T2[Y][X] = ch
        elif mtn:
            T2[Y][X] = "S" if sum(t1(*c) == "S" for c in mtn) * 2 > len(mtn) else "M"
        else:
            cnt = collections.Counter(t1(*c) for c in lnd)
            top = max(cnt.values())
            pick = next(c for c in lnd if cnt[t1(*c)] == top)
            T2[Y][X] = t1(*pick)
            F2[Y][X] = f1(*pick)

t2 = lambda x, y: T2[y][x]
land2 = lambda x, y: t2(x, y) not in WATER + MTN

# 抽样点：V3 陆地每隔 4 格取一个，加上出生点
SAMPLES = [(x, y) for y in range(1, H1, 4) for x in range((y // 4) % 4, W1, 4) if land1(x, y)]
SAMPLES += [(int(x), int(y)) for x, y in re.findall(r'name = "\w+", x = (\d+), y = (\d+)', block(src, "START_POSITIONS").group(1))]
RATIO = (KX + KY) / 2


def problems():
    bad = []
    for s in SAMPLES:
        d1 = bfs(land1, [s], W1, H1)
        s2 = to_v4(*s)
        if not land2(*s2):
            continue
        d2 = bfs(land2, [s2], W2, H2)
        for e in SAMPLES:
            if e <= s:
                continue
            e2 = to_v4(*e)
            if not land2(*e2):
                continue
            a, b = d1.get(e), d2.get(e2)
            if a is None and b is None:
                continue
            if a is None:
                bad.append(("新通道", s, e, None, b))
            elif b is None:
                bad.append(("被堵死", s, e, a, None))
            elif b < a * RATIO * 0.7 - 2:
                bad.append(("捷径", s, e, a, b))
            elif b > a * RATIO * 1.3 + 3:
                bad.append(("绕远", s, e, a, b))
    return bad


def v3_path(s, e):
    par = {s: None}
    q = collections.deque([s])
    while q:
        u = q.popleft()
        if u == e:
            break
        for v in nbrs(*u, W1, H1):
            if v not in par and land1(*v):
                par[v] = u
                q.append(v)
    path, u = [], e
    while u is not None:
        path.append(u)
        u = par[u]
    return path[::-1]


_rep, _near3 = {}, {}


def rep(c):
    """V4 格子对应的 V3 陆地格（收到的来源里最近的陆地格，没有就找最近的 V3 陆地）"""
    if c not in _rep:
        ax, ay = center(*c)
        srcs = sorted(recv.get(c, []), key=lambda s: (center(*s)[0] * KX - ax) ** 2 + (s[1] * KY * SQ - ay) ** 2)
        r = next((s for s in srcs if land1(*s)), None)
        if r is None:
            D = bfs(lambda x, y: True, [to_v3(*c)], W1, H1, 3)
            r = next((s for s in sorted(D, key=D.get) if land1(*s)), to_v3(*c))
        _rep[c] = r
    return _rep[c]


def near3(a, b):
    if a not in _near3:
        _near3[a] = bfs(land1, [a], W1, H1, 6)
    return b in _near3[a]


def safe(v):
    """挖开 v 只连起 V3 里本来就离得近的陆地（两两陆路不超过 6 格），不会造出捷径"""
    reps = {rep(n) for n in nbrs(*v, W2, H2) if land2(*n)}
    reps.add(rep(v))
    reps = [r for r in reps if land1(*r)]
    for r in reps:
        if r not in _near3:
            _near3[r] = bfs(land1, [r], W1, H1, 6)
        if any(o not in _near3[r] for o in reps):
            return False
    return True


def carve(s, e):
    """沿 V3 原来的陆路，在 V4 里挖开一条不过水的路；返回挖开的格数"""
    import heapq
    p1 = v3_path(s, e)
    origin = {}
    for c in p1:
        origin.setdefault(to_v4(*c), c)
    band = set(origin)
    for c in list(origin):
        band.update(nbrs(*c, W2, H2))
    a, b = to_v4(*s), to_v4(*e)
    dist, par = {a: 0}, {a: None}
    pq = [(0, a)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == b:
            break
        if d > dist[u]:
            continue
        for v in nbrs(*u, W2, H2):
            if v not in band:
                continue
            if land2(*v) and land2(*u):
                step = 1
            elif not near3(rep(u), rep(v)):
                continue  # 新挖的相邻两格在 V3 里也必须离得近
            elif land2(*v):
                step = 1
            elif safe(v):
                step = 15 if t2(*v) in WATER else 6
            else:
                continue
            nd = d + step
            if nd < dist.get(v, 1e9):
                dist[v], par[v] = nd, u
                heapq.heappush(pq, (nd, v))
    if b not in par:
        return 0
    n, u = 0, b
    while u is not None:
        if not land2(*u):
            # 取最近的 V3 路径格的地形
            ux, uy = center(*u)
            src_c = min(p1, key=lambda c: (center(*c)[0] * KX - ux) ** 2 + (c[1] * KY * SQ - uy) ** 2)
            T2[u[1]][u[0]] = t1(*src_c)
            F2[u[1]][u[0]] = f1(*src_c)
            n += 1
        u = par[u]
    return n


for it in range(int(os.environ.get("CARVE_ROUNDS", 8))):
    bad = [b for b in problems() if b[0] in ("被堵死", "绕远")]
    if not bad:
        break
    carved = sum(carve(s, e) for _, s, e, *_ in bad)
    print(f"第 {it + 1} 轮修通道：{len(bad)} 对有问题，挖开 {carved} 格山或水")
    if carved == 0:
        break
for (X, Y), ch in FIXES.items():
    T2[Y][X] = ch
    if ch in WATER + MTN:
        F2[Y][X] = "."


# ---- 检查：陆路距离缩放后是否成比例 ----
def check():
    bad = problems()
    kinds = collections.Counter(k for k, *_ in bad)
    print(f"陆路检查（{len(SAMPLES)} 个抽样点两两比较）：", dict(kinds) or "全部正常")
    for k, s, e, a, b in bad[:40]:
        print(f"  {k}: V3 {s} -> {e}  V3 距离 {a}  V4 {to_v4(*s)} -> {to_v4(*e)} 距离 {b}")
    # 水面连通块
    def comps(W, H, f):
        seen, n = set(), 0
        for y in range(H):
            for x in range(W):
                if (x, y) not in seen and f(x, y):
                    n += 1
                    for c in bfs(f, [(x, y)], W, H):
                        seen.add(c)
        return n
    # 定位捷径：沿 V4 最短路逐格对回 V3，V3 里相距很远的相邻两格就是漏洞
    leaks = collections.Counter()
    for k, s, e, a, b in bad:
        if k not in ("捷径", "新通道"):
            continue
        a2, b2 = to_v4(*s), to_v4(*e)
        par = {a2: None}
        q = collections.deque([a2])
        while q:
            u = q.popleft()
            for v in nbrs(*u, W2, H2):
                if v not in par and land2(*v):
                    par[v] = u
                    q.append(v)
        u = b2
        while par[u] is not None:
            v = par[u]
            r1, r2 = rep(u), rep(v)
            if r1 not in _near3:
                _near3[r1] = bfs(land1, [r1], W1, H1, 6)
            if r2 not in _near3[r1]:
                leaks[tuple(sorted([u, v]))] += 1
            u = v
    for (u, v), n in leaks.most_common(20):
        print(f"  漏洞：V4 {u}-{v}（V3 {rep(u)}-{rep(v)}）出现在 {n} 对捷径里")
    print("水面连通块 V3/V4：", comps(W1, H1, lambda x, y: t1(x, y) in WATER), comps(W2, H2, lambda x, y: t2(x, y) in WATER))
    print("陆地连通块 V3/V4：", comps(W1, H1, land1), comps(W2, H2, land2))


check()
if CHECK:
    sys.exit()


# ---- 写回 V4 ----
def fmt_rows(rows):
    return "\n".join('\t"' + "".join(r) + '",' for r in reversed(rows)).rstrip(",")


out = open(V4, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in out else "\n"


def put(name, body):
    global out
    m = block(out, name)
    out = out[:m.start(1)] + nl + body.replace("\n", nl) + out[m.end(1):]


def occupied_free(cells):
    """坐标去重，保持顺序"""
    seen, res = set(), []
    for c in cells:
        if c not in seen:
            seen.add(c)
            res.append(c)
    return res


# rows: T2[Y] 是第 Y 行（南起），写回时北在上
put("TERRAIN_ROWS", fmt_rows(T2))
put("FEATURE_ROWS", fmt_rows(F2))
v3body = lambda name: block(src, name).group(1)


def nearest_flat(x, y):
    """出生点、城址必须是能坐城的平地：不是的话挪到最近的平地/丘陵"""
    if t2(x, y) in "gpdGPD":
        return x, y
    for r in range(1, 4):
        D = bfs(lambda a, b: True, [(x, y)], W2, H2, r)
        for c in sorted(D, key=lambda c: (D[c], c)):
            if t2(*c) in "gp":
                return c
    return x, y


# 出生点
starts = re.findall(r'\{ name = "(\w+)", x = (\d+), y = (\d+) \}', v3body("START_POSITIONS"))
lines = []
for n, x, y in starts:
    X, Y = nearest_flat(*to_v4(int(x), int(y)))
    lines.append(f'\t{{ name = "{n}", x = {X}, y = {Y} }}')
put("START_POSITIONS", ",\n".join(lines))
START4 = {n: nearest_flat(*to_v4(int(x), int(y))) for n, x, y in starts}


# 资源类（x, y, res）：同一格只留第一个，落在水里的水产资源保留、陆地资源落到水里就丢掉
def cat(ch):
    return "w" if ch in WATER else "m" if ch in MTN else "l"


def scale_res(name):
    used, lines, drop, moved = set(), [], 0, 0
    for x, y, r in re.findall(r'\{ x = (\d+), y = (\d+), res = "(\w+)" \}', v3body(name)):
        x, y = int(x), int(y)
        X, Y = to_v4(x, y)
        if cat(t2(X, Y)) != cat(t1(x, y)):
            # 缩放后地形类型变了（陆地资源落到山上或水里）：2 格内找最近的同类格，优先地形完全相同的
            D = bfs(lambda a, b: True, [(X, Y)], W2, H2, 2)
            ok = [c for c in D if cat(t2(*c)) == cat(t1(x, y)) and c not in used and c not in START4.values()]
            if not ok:
                drop += 1
                continue
            X, Y = min(ok, key=lambda c: (D[c], t2(*c) != t1(x, y), c))
            moved += 1
        if (X, Y) in used or (X, Y) in START4.values():
            drop += 1
            continue
        used.add((X, Y))
        lines.append(f'\t{{ x = {X}, y = {Y}, res = "{r}" }}')
    put(name, ",\n".join(lines))
    print(f"{name}: {len(lines)} 处（挪到邻格 {moved} 处，合并或丢掉 {drop} 处）")


for name in ("SITE_RESOURCES", "GUAR_RESOURCES", "SCATTER_RESOURCES"):
    scale_res(name)


def scale_cells(name, keep=lambda X, Y: True):
    cells = occupied_free(to_v4(int(x), int(y)) for x, y in re.findall(r"\{ x = (\d+), y = (\d+) \}", v3body(name)))
    cells = [c for c in cells if keep(*c)]
    put(name, ",\n".join(f"\t{{ x = {X}, y = {Y} }}" for X, Y in cells))
    print(f"{name}: {len(cells)} 格")


scale_cells("KEEP_CELLS")
# 黄河（函谷—洛阳段）是一整排格子的南侧河边：缩放两端，中间连成一排，山地格也保留（河贴着山南麓）
ys = [(int(x), int(y)) for x, y in re.findall(r"\{ x = (\d+), y = (\d+) \}", v3body("YELLOW_EDGE_CELLS"))]
(xa, ya), (xb, _) = to_v4(*ys[0]), to_v4(*ys[-1])
put("YELLOW_EDGE_CELLS", ",\n".join(f"\t{{ x = {X}, y = {ya} }}" for X in range(xa, xb + 1)))
print(f"YELLOW_EDGE_CELLS: {xb - xa + 1} 格（第 {ya} 行 x={xa}..{xb}）")
scale_cells("CLIFF_CELLS", land2)
scale_cells("LEY_CANDIDATES", land2)

# 河边：两端都缩放，仍是相邻的两块陆地才保留（之后用 connect_rivers.py 接通）
body = v3body("RIVER_PAIRS")
seen, lines = set(), []
for line in body.splitlines():
    m = re.match(r"\s*\{ (\d+), (\d+), (\d+), (\d+) \}", line)
    if not m:
        if line.strip().startswith("--"):
            lines.append(line.rstrip())
        continue
    a = to_v4(int(m[1]), int(m[2]))
    b = to_v4(int(m[3]), int(m[4]))
    key = tuple(sorted([a, b]))
    if a == b or key in seen or b not in set(nbrs(*a, W2, H2)) or not (land2(*a) and land2(*b)):
        continue
    seen.add(key)
    lines.append(f"\t{{ {a[0]}, {a[1]}, {b[0]}, {b[1]} }},")
# 去掉末尾逗号，去掉后面没有河边的注释
while lines and lines[-1].strip().startswith("--"):
    lines.pop()
lines[-1] = lines[-1].rstrip(",")
put("RIVER_PAIRS", "\n".join(lines))
print(f"RIVER_PAIRS: {len(seen)} 条河边")


# 矩形区域
def scale_box(text, name):
    def rep(m):
        x1, y1 = to_v4(int(m[2]), int(m[4]))
        x2, y2 = to_v4(int(m[3]), int(m[5]))
        return f"{m[1]}x1 = {x1}, x2 = {x2}, y1 = {y1}, y2 = {y2}"
    m = block(text, name)
    body = re.sub(r"(.*?)x1 = (\d+), x2 = (\d+), y1 = (\d+), y2 = (\d+)", rep, m.group(1))
    return text[:m.start(1)] + body + text[m.end(1):]


out = scale_box(out, "GRANARIES")
out = re.sub(r"local MAP_W, MAP_H = \d+, \d+", f"local MAP_W, MAP_H = {W2}, {H2}", out)
open(V4, "w", encoding="utf-8", newline="").write(out)

# 游戏内脚本：城址和蛮族区
g = open(V4_GAMEPLAY, encoding="utf-8", newline="").read()
g3 = open(os.path.join(V3_DIR, "ZhanguoV3_Gameplay.lua"), encoding="utf-8", newline="").read()
m3 = block(g3, "SITES")
sites = re.sub(r"x = (\d+), y = (\d+)", lambda m: "x = %d, y = %d" % nearest_flat(*to_v4(int(m[1]), int(m[2]))), m3.group(1))
m = block(g, "SITES")
g = g[:m.start(1)] + sites + g[m.end(1):]
m = block(g, "BARB_ZONES")
g = g[:m.start(1)] + block(scale_box(g3, "BARB_ZONES"), "BARB_ZONES").group(1) + g[m.end(1):]
open(V4_GAMEPLAY, "w", encoding="utf-8", newline="").write(g)

# 选址规划.md 的关隘坐标表
p3 = open(os.path.join(V3_DIR, "选址规划.md"), encoding="utf-8", newline="").read()
head, tail = p3.split("## 关隘坐标", 1)
tail = re.sub(r"\((\d+), (\d+)\)", lambda m: "(%d, %d)" % to_v4(int(m[1]), int(m[2])), tail)
open(V4_PLAN, "w", encoding="utf-8", newline="").write(head + "## 关隘坐标" + tail)
print("已写入 V4")
