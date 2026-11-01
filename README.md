# 战国七雄 V4 · Warring States China Map (Standard)

文明六固定地形地图：秦、楚、齐、燕、韩、赵、魏与周，关中四塞、蜀道、三峡夷陵、太行八陉。标准尺寸 84×54，给 2~5 名真人对战，其余位置可以用人机补。

- 由巨型的 V3（106×66，在 [mapzg-cv6](https://github.com/SEUhajimi/mapzg-cv6) 仓库）等比缩小而来，山脉、关隘和河流的走向保持不变。
- 出生点在各国历史都城，周围 3 格的陆地、粮食、生产力和丘陵调平过。
- 开局组合按对战重算：2~5 人时各家开局附近的土地相差不超过 6%，每家离最近的邻居不超过 24 格。
- 带有历史地名、北方边患、粮仓；没有 V3 的行军加速。

当前版本和确认方法见 [`Zhanguo_V4/版本.txt`](Zhanguo_V4/版本.txt)，地图预览在 [`Zhanguo_V4/地图预览/`](Zhanguo_V4/地图预览/)。

## 安装

把 `Zhanguo_V4` 文件夹复制到 `文档\My Games\Sid Meier's Civilization VI\Mods\`（先删除同名旧文件夹），在游戏「附加内容」中启用，选图时选「战国七雄 V4（标准）」。V4 和 V3 的 mod ID 不同，可以同时启用。仓库里的其他内容不用放进游戏。

## 开发工具（不进游戏）

工具默认处理 `Zhanguo_V4/ZhanguoV4.lua`。

- `tools/render_map.py`：生成 `地图预览/` 下的预览图。需要 Pillow。
- `tools/start_sets.py`：重算开局距离表和开局组合，`--write` 写回地图脚本。需要 numpy。
- `tools/connect_rivers.py`：把不通水面的河段接到最近的水面。
- `tools/balance_starts.py`：调平各出生点 3 格内的地形，`--write` 写回。
- `tools/scale_v4.py`：把 V3 等比缩小成 V4 的一次性转换工具，读旁边 `mapzg-cv6` 仓库里的 V3（已经用过，再运行会覆盖 V4 调平过的地形）。
- `tools/build_workshop.py`：`python tools/build_workshop.py Zhanguo_V4` 生成创意工坊上传文件夹。

Fixed-terrain Warring States China map for Civilization VI, Standard size (84×54), balanced for 2-5 player PvP. Scaled down from the Huge V3 map. Copy `Zhanguo_V4` into your `Mods` folder to install.
