# CLAUDE.md

文明六固定地形地图 mod「战国七雄 V4」：标准 84×54，给 2~5 人对战用（其余位置人机补）。进游戏的文件都在 `Zhanguo_V4/`。

V4 由巨型的 V3（旁边的 `E:\GitHub-Repos\mapzg-cv6` 仓库，`Zhanguo_V3/`）等比缩小而来（`tools/scale_v4.py`，一次性），出生点周围地形调平过，没有 V3 的行军加速。两个 mod 的 mod ID 不同，可同时启用。V4 的地图脚本代码和 V3 一样，只有数据块和少数常数（自然奇观数、资源抽稀步长）不同；改了地图脚本的代码时，看看 V3 要不要同步。地名文本键（`LOC_ZHANGUO_CITY_*`）和 V3 相同，因为两边都只在选了自己地图时加载，不会冲突；其他文本键用 `ZHANGUOV4_` 前缀。

## 结构

- `Zhanguo_V4/ZhanguoV4.lua`：地图脚本，地形（`TERRAIN_ROWS`）、河流（`RIVER_PAIRS`、`YELLOW_EDGE_CELLS`）、资源、出生点、开局组合（`SPREAD_SETS`）都在这里。
- `Zhanguo_V4/版本.txt`、`.modinfo`、`ZhanguoV4_Text.xml`、地图脚本开头和 `print` 里都写着版本号，**发版时一起改**。
- `Zhanguo_V4/ZhanguoV4_Gameplay.lua`：游戏内脚本，只在选了这张地图时加载（`.modinfo` 按 `MAP_SCRIPT` 判断）。①城市历史地名：主要文明在城址（`SITES`）2 格内建城时改名，名字的本地化文本在 `ZhanguoV4_CityNames.xml`；②北方边患：`BARB_ZONES` 里的区域定期补蛮族营地。
- `Zhanguo_V4/选址规划.md`：城址和关隘说明，末尾的“关隘坐标”表供 `render_map.py` 标注。

## 工具（默认处理 Zhanguo_V4/ZhanguoV4.lua）

- `tools/render_map.py`：把地形画成 `地图预览/` 下的预览图（全图、七张分区图和关隘标注图）。关隘位置只作参考。需要 Pillow。
- `tools/start_sets.py`：按地形重算开局距离表 `START_DIST` 和各人数（2 人起）的开局组合 `SPREAD_SETS`，不带参数只打印，`--write` 写回。需要 numpy。只比较离出生点 `REACH`（10）格内的陆地，每家离最近邻居不超过 `MAX_NEAR`，最小间距 `MIN_GAP` 按地图宽度换算。
- `tools/balance_starts.py`：给每个出生点 3 格内的陆地、粮食、生产力、丘陵定下限，不够的改地形补（山改丘陵前检查不会开出新通道），`--write` 写回。南京四面是水，生产力达不到下限，是已知情况。
- `tools/open_pockets.py`：找出被山围住、走不进去的小块陆地，沿最少的山格挖到外面的大块（挖开的山改丘陵），挖前检查只多出死胡同、不会开出新通道，`--write` 写回。V4 正常应只剩 4 块陆地（中原主陆、四川盆地、西南两块，和 V3 一致）。
- `tools/connect_rivers.py`：游戏里的河必须流进水里，不通水的河段末端会画出小水坑。这个工具把这类河段接到最近的水面，可重复运行。
- `tools/scale_v4.py`：V3→V4 的一次性转换（读 `../mapzg-cv6/Zhanguo_V3/`）。V4 之后又被 balance_starts.py 改过地形，**不要再运行**，否则覆盖 V4 的地形和数据块。
- 改了地形后依次运行 `open_pockets.py --write`、`connect_rivers.py`、`balance_starts.py --write`、`start_sets.py --write` 和 `render_map.py`。
- `tools/build_workshop.py`：`python tools/build_workshop.py Zhanguo_V4` 按 `.modinfo` 的 `<Files>` 把要上传的文件复制到 `dist/workshop/Zhanguo_V4/`（已 gitignore）。工坊预览图（<1MB）和介绍（BBCode）在 `workshop/Zhanguo_V4/`。

## 网页编辑器（和用户协同微调）

- 页面：https://claude.ai/artifact/DyPWeW3WLY3DxeJ8nQCUsT （私有，只有用户能打开）。由 `tools/build_editor.py` 用 `tools/editor_template.html` 生成到 `dist/editor/map_editor.html`，再用 Artifact 工具发布到同一个 URL（声明 `capabilities: {db: {}}`）。
- 用户在页面上改的格子存在数据库 `edits` 集合，文档 id 为 `x-y`，字段 x、y、t、f（地形/地貌字符）、bt、bf（改之前）、note（备注）。只有备注、没改地形的条目要按备注手动处理。
- 用户说「改好了」时：ArtifactData `list` 读 `edits`（`out_dir` 存成 JSON）→ 合成一个列表文件 → `python tools/apply_edits.py <文件>` 先预览、再 `--write` → 依次运行 `open_pockets.py --write`、`connect_rivers.py`、`balance_starts.py --write`、`start_sets.py --write`、`render_map.py` → 向用户汇报 → `build_editor.py` 重新生成并发布页面（新底图）→ 用 ArtifactData `batch` 删掉已应用的 edits 文档。

## 约定

- 代码注释、脚本说明用中文。
- 提交信息用英文，**不要添加 Claude 的 `Co-Authored-By` 署名**。
- 只在用户要求时提交。
- 没有自动化测试，改动最终需要用户进游戏验证。日志在 `%LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VI\Logs\`（`Lua.log`、`Database.log`、`Modding.log`）。修改 `.modinfo` 后要重启游戏；只改 Lua / SQL 时重新读档即可。
- 游戏 `Mods\Zhanguo_V4` 是指向本仓库 `Zhanguo_V4` 的链接。`Mods\` 里不能留下失效的链接，否则游戏可能找不到排在它后面的 mod。
- 联机时所有玩家的 mod 文件必须完全一致，否则会不同步。Gameplay 脚本只在 `GameEvents.*` 回调里改游戏状态，不要在 `Events.*` 或脚本加载时改。
- 文明六 mod 机制教程见文明征服模式仓库的 `docs/modding-guide.md`。
