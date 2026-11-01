"""
把被山围住的小块陆地接到外面的大块陆地上，让单位（建造者）能走进去开发。

陆地按“能走过去”分块（山和水不算陆地）。小于 POCKET_MAX 格的块算“小块”，
沿最少的山格挖到相邻的大块（POCKET_MAX 格以上），挖开的山改成丘陵（地形跟小块里的多数）。
挖之前检查：挖开的格子周围、小块以外的陆地，不经过新口子也能在 len(路径)+3 格内互通，
并且都属于同一个大块，所以只多出一条死胡同，不会开出新的关隘或捷径。
找不到安全口子的小块会列出来，需要手动处理。可重复运行，没有小块时不再改动。

用法：python tools/open_pockets.py [地图脚本] [--write]
"""
import collections
import heapq
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
LUA = args[0] if args else os.path.join(ROOT, "Zhanguo_V4", "ZhanguoV4.lua")
WRITE = "--write" in sys.argv
POCKET_MAX = 20  # V4 里四大块最小的也有 34 格，小块最大 10 格
MAX_DIG = 3      # 最多挖几格山

s = open(LUA, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"
blk = lambda n: re.search(r"local " + n + r" = \{(.*?)\r?\n\}", s, re.S)
T = [list(r) for r in re.findall(r'"([^"]+)"', blk("TERRAIN_ROWS").group(1))]
H, W = len(T), len(T[0])
t = lambda x, y: T[H - 1 - y][x]


def sett(x, y, c):
    T[H - 1 - y][x] = c


res = set()
for name in ("SITE_RESOURCES", "GUAR_RESOURCES", "SCATTER_RESOURCES"):
    res |= {(int(x), int(y)) for x, y in re.findall(r"x = (\d+), y = (\d+)", blk(name).group(1))}


def nbrs(x, y):
    d = [(1, 0), (-1, 0), (0, 1), (1, 1), (0, -1), (1, -1)] if y & 1 else [(1, 0), (-1, 0), (-1, 1), (0, 1), (-1, -1), (0, -1)]
    for dx, dy in d:
        if 0 <= x + dx < W and 0 <= y + dy < H:
            yield x + dx, y + dy


land = lambda x, y: t(x, y) not in "~cMS"
mtn = lambda x, y: t(x, y) in "MS"


def components():
    comp, sizes = {}, []
    for x in range(W):
        for y in range(H):
            if land(x, y) and (x, y) not in comp:
                k = len(sizes)
                comp[(x, y)] = k
                q, n = [(x, y)], 0
                while q:
                    u = q.pop()
                    n += 1
                    for v in nbrs(*u):
                        if land(*v) and v not in comp:
                            comp[v] = k
                            q.append(v)
                sizes.append(n)
    return comp, sizes


def land_dist(a, limit, block):
    """a 出发，只走陆地、不经过 block，limit 格内的距离"""
    D = {a: 0}
    q = collections.deque([a])
    while q:
        u = q.popleft()
        if D[u] >= limit:
            continue
        for v in nbrs(*u):
            if v not in D and v not in block and land(*v):
                D[v] = D[u] + 1
                q.append(v)
    return D


def find_gate(pocket, comp, sizes):
    """沿最少的山格从小块挖到大块，返回 (山格路径, 目标块) 或 None；按挖格数从少到多逐个检查安全"""
    pk = comp[next(iter(pocket))]
    start = [(0, c, ()) for c in pocket]
    heap = list(start)
    heapq.heapify(heap)
    best = {c: 0 for c in pocket}
    tried = set()
    while heap:
        d, u, path = heapq.heappop(heap)
        if d > MAX_DIG:
            break
        for v in nbrs(*u):
            if land(*v) and comp.get(v, pk) != pk and sizes[comp[v]] >= POCKET_MAX and path:
                key = (path, comp[v])
                if key in tried:
                    continue
                tried.add(key)
                if safe(path, pocket, comp[v], comp):
                    return path, comp[v]
            if mtn(*v) and v not in path and v not in res:
                nd = d + 1
                if nd <= MAX_DIG and best.get(v, 99) >= nd:
                    best[v] = nd
                    heapq.heappush(heap, (nd, v, path + (v,)))
    return None


def safe(path, pocket, target, comp):
    block = set(path)
    outside = {v for p in path for v in nbrs(*p) if land(*v) and v not in pocket}
    if not outside or any(comp.get(v) != target for v in outside):
        return False
    lim = len(path) + 3
    ol = sorted(outside)
    D = land_dist(ol[0], lim, block | set(pocket))
    return all(v in D for v in ol)


comp, sizes = components()
pockets = collections.defaultdict(set)
for c, k in comp.items():
    if sizes[k] < POCKET_MAX:
        pockets[k].add(c)

log, fail = [], []
for k, cells in sorted(pockets.items(), key=lambda kv: min(kv[1])):
    g = find_gate(cells, comp, sizes)
    if g is None:
        fail.append(cells)
        continue
    path, _ = g
    terr = "".join(t(*c) for c in cells)
    hill = "G" if sum(ch in "gG" for ch in terr) > len(terr) / 2 else "D" if sum(ch in "dD" for ch in terr) > len(terr) / 2 else "P"
    for p in path:
        sett(*p, hill)
    nres = sum(c in res for c in cells)
    log.append((min(cells), len(cells), nres, path, hill))

for c, n, r, path, hill in log:
    print(f"小块 {c} {n} 格（资源 {r}）：挖开 {list(path)} → {hill}")
for cells in fail:
    print(f"找不到安全口子：{sorted(cells)}")
comp2, sizes2 = components()
print("陆地块大小：", sorted(sizes2, reverse=True)[:8], f"共 {len(sizes2)} 块")

if WRITE and log:
    m = blk("TERRAIN_ROWS")
    body = nl + ("," + nl).join('\t"' + "".join(r) + '"' for r in T)
    s = s[:m.start(1)] + body + s[m.end(1):]
    open(LUA, "w", encoding="utf-8", newline="").write(s)
    print(f"已写回 {sum(len(p) for _, _, _, p, _ in log)} 格")
