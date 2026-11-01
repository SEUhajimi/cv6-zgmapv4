-- =============================================================================
-- 战国七雄：游戏内脚本（只在选了这张地图时加载）
--
-- 1. 城市历史地名：主要文明在某个历史城址 2 格内建城时，城市改用这个城址的名字
--    （最近的、还没被其他城市用掉的那个）。名字是本地化键，见 ZhanguoV4_CityNames.xml。
-- 2. 北方边患：阴山以北、河套和燕代以北每隔几回合检查一次，蛮族营地少于目标数就补一个，
--    补在没人看得见、离城市够远的空地上。没开蛮族或进入工业时代后不再补。
--
-- 联机：只在 GameEvents 回调里改游戏状态，随机数用 Game.GetRandNum，所有机器结果一致。
-- =============================================================================

local SITES = {
	{ key = "LOC_ZHANGUO_CITY_HANDAN", x = 51, y = 35 },  -- 邯郸
	{ key = "LOC_ZHANGUO_CITY_JINYANG", x = 44, y = 40 },  -- 晋阳
	{ key = "LOC_ZHANGUO_CITY_XIANYANG", x = 29, y = 26 },  -- 咸阳
	{ key = "LOC_ZHANGUO_CITY_LUOYANG", x = 43, y = 27 },  -- 洛阳
	{ key = "LOC_ZHANGUO_CITY_XIANGYANG", x = 42, y = 18 },  -- 襄阳
	{ key = "LOC_ZHANGUO_CITY_CHENGDU", x = 10, y = 12 },  -- 成都
	{ key = "LOC_ZHANGUO_CITY_HEFEI", x = 61, y = 15 },  -- 合肥
	{ key = "LOC_ZHANGUO_CITY_ANYI", x = 39, y = 30 },  -- 安邑
	{ key = "LOC_ZHANGUO_CITY_JI", x = 59, y = 48 },  -- 蓟
	{ key = "LOC_ZHANGUO_CITY_LINZI", x = 67, y = 36 },  -- 临淄
	{ key = "LOC_ZHANGUO_CITY_PENGCHENG", x = 62, y = 27 },  -- 彭城
	{ key = "LOC_ZHANGUO_CITY_JIANGZHOU", x = 19, y = 9 },  -- 江州
	{ key = "LOC_ZHANGUO_CITY_JINLING", x = 69, y = 16 },  -- 金陵
	{ key = "LOC_ZHANGUO_CITY_KUAIJI", x = 74, y = 9 },  -- 会稽
	{ key = "LOC_ZHANGUO_CITY_HANZHONG", x = 21, y = 21 },  -- 汉中
	{ key = "LOC_ZHANGUO_CITY_DALIANG", x = 52, y = 27 },  -- 大梁
	{ key = "LOC_ZHANGUO_CITY_ZHONGSHAN", x = 53, y = 43 },  -- 中山
	{ key = "LOC_ZHANGUO_CITY_E", x = 52, y = 9 },  -- 鄂
	{ key = "LOC_ZHANGUO_CITY_TONGGUAN", x = 33, y = 27 },  -- 潼关
	{ key = "LOC_ZHANGUO_CITY_HANGUGUAN", x = 38, y = 27 },  -- 函谷关
	{ key = "LOC_ZHANGUO_CITY_BAOXIEDAO", x = 24, y = 23 },  -- 褒斜道
	{ key = "LOC_ZHANGUO_CITY_QISHANDAO", x = 13, y = 25 },  -- 祁山道
	{ key = "LOC_ZHANGUO_CITY_SHANGWUDAO", x = 34, y = 26 },  -- 商於道
	{ key = "LOC_ZHANGUO_CITY_WUGUAN", x = 35, y = 22 },  -- 武关
	{ key = "LOC_ZHANGUO_CITY_SANGUAN", x = 21, y = 25 },  -- 散关
	{ key = "LOC_ZHANGUO_CITY_SANGUANKOU", x = 19, y = 43 },  -- 三关口
	{ key = "LOC_ZHANGUO_CITY_WUSHAOLING", x = 8, y = 41 },  -- 乌鞘岭
	{ key = "LOC_ZHANGUO_CITY_ZHIDAO", x = 29, y = 33 },  -- 直道
	{ key = "LOC_ZHANGUO_CITY_XIAOGUAN", x = 19, y = 33 },  -- 萧关
	{ key = "LOC_ZHANGUO_CITY_LONGQUANYI", x = 13, y = 12 },  -- 龙泉驿
	{ key = "LOC_ZHANGUO_CITY_JIANYANG", x = 14, y = 10 },  -- 简阳
	{ key = "LOC_ZHANGUO_CITY_JIANMENGUAN", x = 16, y = 19 },  -- 剑门关
	{ key = "LOC_ZHANGUO_CITY_MICANGDAO", x = 21, y = 19 },  -- 米仓道
	{ key = "LOC_ZHANGUO_CITY_BAIDICHENG", x = 32, y = 15 },  -- 白帝城
	{ key = "LOC_ZHANGUO_CITY_QUTANGGUAN", x = 30, y = 11 },  -- 瞿塘关
	{ key = "LOC_ZHANGUO_CITY_YINPING", x = 10, y = 19 },  -- 阴平
	{ key = "LOC_ZHANGUO_CITY_QINGMUGUAN", x = 16, y = 9 },  -- 青木关
	{ key = "LOC_ZHANGUO_CITY_TONGCHENGKOU", x = 51, y = 7 },  -- 通城口
	{ key = "LOC_ZHANGUO_CITY_PINGJINGGUAN", x = 50, y = 18 },  -- 平靖关
	{ key = "LOC_ZHANGUO_CITY_WUSHENGGUAN", x = 51, y = 19 },  -- 武胜关
	{ key = "LOC_ZHANGUO_CITY_JIULIGUAN", x = 53, y = 16 },  -- 九里关
	{ key = "LOC_ZHANGUO_CITY_YOUSHUIKOU", x = 26, y = 3 },  -- 酉水口
	{ key = "LOC_ZHANGUO_CITY_HULAOGUAN", x = 48, y = 28 },  -- 虎牢关
	{ key = "LOC_ZHANGUO_CITY_ZHIGUAN", x = 40, y = 31 },  -- 轵关
	{ key = "LOC_ZHANGUO_CITY_PUJINGUAN", x = 35, y = 29 },  -- 蒲津关
	{ key = "LOC_ZHANGUO_CITY_GAOQUE", x = 23, y = 50 },  -- 高阙
	{ key = "LOC_ZHANGUO_CITY_JIUYUAN", x = 33, y = 50 },  -- 九原塞
	{ key = "LOC_ZHANGUO_CITY_JINGXINGGUAN", x = 50, y = 41 },  -- 井陉关
	{ key = "LOC_ZHANGUO_CITY_FEIHUDAO", x = 51, y = 47 },  -- 飞狐道
	{ key = "LOC_ZHANGUO_CITY_YANMENGUAN", x = 43, y = 44 },  -- 雁门关
	{ key = "LOC_ZHANGUO_CITY_JUYONGGUAN", x = 59, y = 50 },  -- 居庸关
	{ key = "LOC_ZHANGUO_CITY_GUBEIKOU", x = 62, y = 49 },  -- 古北口
	{ key = "LOC_ZHANGUO_CITY_MULINGGUAN", x = 68, y = 32 },  -- 穆陵关
	{ key = "LOC_ZHANGUO_CITY_TAIHANGXING", x = 45, y = 31 },  -- 太行陉
	{ key = "LOC_ZHANGUO_CITY_FUKOUXING", x = 49, y = 35 },  -- 滏口陉
	{ key = "LOC_ZHANGUO_CITY_MENGJIN", x = 44, y = 28 },  -- 孟津
	{ key = "LOC_ZHANGUO_CITY_FANGCHENG", x = 45, y = 23 },  -- 方城
	{ key = "LOC_ZHANGUO_CITY_LUYANGGUAN", x = 43, y = 23 },  -- 鲁阳关
	{ key = "LOC_ZHANGUO_CITY_YONG", x = 24, y = 26 },  -- 雍
	{ key = "LOC_ZHANGUO_CITY_LIYANG", x = 31, y = 28 },  -- 栎阳
	{ key = "LOC_ZHANGUO_CITY_LANTIAN", x = 31, y = 26 },  -- 蓝田
	{ key = "LOC_ZHANGUO_CITY_DIDAO", x = 9, y = 30 },  -- 狄道
	{ key = "LOC_ZHANGUO_CITY_TIANSHUI", x = 16, y = 29 },  -- 天水
	{ key = "LOC_ZHANGUO_CITY_SHANGJUN", x = 34, y = 41 },  -- 上郡
	{ key = "LOC_ZHANGUO_CITY_LINQIONG", x = 7, y = 11 },  -- 临邛
	{ key = "LOC_ZHANGUO_CITY_LANGZHONG", x = 18, y = 16 },  -- 阆中
	{ key = "LOC_ZHANGUO_CITY_BODAO", x = 12, y = 6 },  -- 僰道
	{ key = "LOC_ZHANGUO_CITY_ZHI", x = 24, y = 8 },  -- 枳
	{ key = "LOC_ZHANGUO_CITY_YILING", x = 38, y = 14 },  -- 夷陵
	{ key = "LOC_ZHANGUO_CITY_YING", x = 41, y = 13 },  -- 郢
	{ key = "LOC_ZHANGUO_CITY_WAN", x = 44, y = 20 },  -- 宛
	{ key = "LOC_ZHANGUO_CITY_YAN", x = 44, y = 18 },  -- 鄢
	{ key = "LOC_ZHANGUO_CITY_XIAKOU", x = 51, y = 12 },  -- 夏口
	{ key = "LOC_ZHANGUO_CITY_CHEN", x = 53, y = 24 },  -- 陈
	{ key = "LOC_ZHANGUO_CITY_SHOUCHUN", x = 60, y = 18 },  -- 寿春
	{ key = "LOC_ZHANGUO_CITY_JIANGPU", x = 66, y = 17 },  -- 江浦
	{ key = "LOC_ZHANGUO_CITY_RUXUWU", x = 65, y = 15 },  -- 濡须坞
	{ key = "LOC_ZHANGUO_CITY_RUXUKOU", x = 65, y = 11 },  -- 濡须口
	{ key = "LOC_ZHANGUO_CITY_GUSU", x = 74, y = 12 },  -- 姑苏
	{ key = "LOC_ZHANGUO_CITY_CHANGSHA", x = 44, y = 3 },  -- 长沙
	{ key = "LOC_ZHANGUO_CITY_WULING", x = 42, y = 6 },  -- 武陵
	{ key = "LOC_ZHANGUO_CITY_LINGLING", x = 42, y = 2 },  -- 零陵
	{ key = "LOC_ZHANGUO_CITY_GUIYANG", x = 50, y = 1 },  -- 桂阳
	{ key = "LOC_ZHANGUO_CITY_YUANLING", x = 34, y = 3 },  -- 沅陵
	{ key = "LOC_ZHANGUO_CITY_YANGZHAI", x = 47, y = 26 },  -- 阳翟
	{ key = "LOC_ZHANGUO_CITY_XINZHENG", x = 48, y = 24 },  -- 新郑
	{ key = "LOC_ZHANGUO_CITY_YIYANG", x = 42, y = 26 },  -- 宜阳
	{ key = "LOC_ZHANGUO_CITY_SHANGDANG", x = 45, y = 33 },  -- 上党
	{ key = "LOC_ZHANGUO_CITY_YE", x = 52, y = 34 },  -- 邺
	{ key = "LOC_ZHANGUO_CITY_JULU", x = 51, y = 37 },  -- 巨鹿
	{ key = "LOC_ZHANGUO_CITY_ZHANGWU", x = 62, y = 42 },  -- 章武
	{ key = "LOC_ZHANGUO_CITY_PINGYUAN", x = 59, y = 42 },  -- 平原
	{ key = "LOC_ZHANGUO_CITY_DUKANG", x = 57, y = 45 },  -- 督亢
	{ key = "LOC_ZHANGUO_CITY_DAI", x = 51, y = 47 },  -- 代
	{ key = "LOC_ZHANGUO_CITY_YI", x = 55, y = 46 },  -- 易
	{ key = "LOC_ZHANGUO_CITY_JIMO", x = 75, y = 34 },  -- 即墨
	{ key = "LOC_ZHANGUO_CITY_JU", x = 69, y = 30 },  -- 莒
	{ key = "LOC_ZHANGUO_CITY_JINAN", x = 59, y = 37 },  -- 济南
}
local NAME_RADIUS = 2

-- 蛮族补营区：x1..x2, y1..y2 范围内保持 target 个营地
local BARB_ZONES = {
	{ name = "Yinshan", x1 = 3, x2 = 44, y1 = 51, y2 = 52, target = 2 },   -- 阴山以北
	{ name = "Hetao", x1 = 17, x2 = 40, y1 = 41, y2 = 48, target = 2 },    -- 河套、鄂尔多斯北部
	{ name = "YanDai", x1 = 42, x2 = 76, y1 = 51, y2 = 51, target = 2 },   -- 燕代以北
}
local BARB_FIRST_TURN = 6      -- 第几回合开始补
local BARB_INTERVAL = 8        -- 每隔几回合检查一次
local BARB_LAST_ERA = 3        -- 文艺复兴时代（含）之后不再补
local BARB_CITY_DIST = 4       -- 离任何城市至少几格
local BARB_CAMP_DIST = 3       -- 离其他营地至少几格

-- -----------------------------------------------------------------------------
-- 1. 城市历史地名
-- -----------------------------------------------------------------------------
local function NameInUse(key)
	for _, pPlayer in ipairs(PlayerManager.GetAlive()) do
		for _, pCity in pPlayer:GetCities():Members() do
			if pCity:GetName() == key then return true end
		end
	end
	return false
end

local function OnCityBuilt(playerID, cityID, x, y)
	local pPlayer = Players[playerID]
	if pPlayer == nil or not pPlayer:IsMajor() then return end
	local pCity = CityManager.GetCity(playerID, cityID)
	if pCity == nil or pCity.SetName == nil then return end
	local best, bestDist = nil, NAME_RADIUS + 1
	for _, s in ipairs(SITES) do
		local d = Map.GetPlotDistance(x, y, s.x, s.y)
		if d < bestDist and pCity:GetName() ~= s.key and not NameInUse(s.key) then
			best, bestDist = s, d
		end
	end
	if best ~= nil then
		pCity:SetName(best.key)
		print("ZhanguoV4: city at (" .. x .. "," .. y .. ") named " .. best.key)
	end
end

-- -----------------------------------------------------------------------------
-- 2. 北方边患
-- -----------------------------------------------------------------------------
local CAMP = GameInfo.Improvements["IMPROVEMENT_BARBARIAN_CAMP"]
local TRIBE_CAVALRY = GameInfo.BarbarianTribes["TRIBE_CAVALRY"]
local TRIBE_MELEE = GameInfo.BarbarianTribes["TRIBE_MELEE"]

local function CampsNear(x, y, r)
	local n = 0
	for dx = -r, r do
		for dy = -r, r do
			local p = Map.GetPlot(x + dx, y + dy)
			if p ~= nil and p:GetImprovementType() == CAMP.Index and Map.GetPlotDistance(x, y, p:GetX(), p:GetY()) <= r then
				n = n + 1
			end
		end
	end
	return n
end

local function CityNear(x, y, r)
	for _, pPlayer in ipairs(PlayerManager.GetAlive()) do
		for _, pCity in pPlayer:GetCities():Members() do
			if Map.GetPlotDistance(x, y, pCity:GetX(), pCity:GetY()) < r then return true end
		end
	end
	return false
end

local function SeenByMajor(plotIndex)
	for _, pPlayer in ipairs(PlayerManager.GetAliveMajors()) do
		local vis = PlayersVisibility[pPlayer:GetID()]
		if vis ~= nil and vis:IsVisible(plotIndex) then return true end
	end
	return false
end

local function CanCamp(p)
	return not p:IsWater() and not p:IsMountain() and not p:IsImpassable() and not p:IsNaturalWonder()
		and p:GetOwner() == -1 and p:GetImprovementType() == -1 and p:GetDistrictType() == -1
		and p:GetUnitCount() == 0
end

local function FillZone(z)
	local have = 0
	for y = z.y1, z.y2 do
		for x = z.x1, z.x2 do
			local p = Map.GetPlot(x, y)
			if p ~= nil and p:GetImprovementType() == CAMP.Index then have = have + 1 end
		end
	end
	if have >= z.target then return end
	local cands = {}
	for y = z.y1, z.y2 do
		for x = z.x1, z.x2 do
			local p = Map.GetPlot(x, y)
			if p ~= nil and CanCamp(p) and not SeenByMajor(p:GetIndex())
				and not CityNear(x, y, BARB_CITY_DIST) and CampsNear(x, y, BARB_CAMP_DIST - 1) == 0 then
				cands[#cands + 1] = p
			end
		end
	end
	if #cands == 0 then return end
	local p = cands[Game.GetRandNum(#cands, "Zhanguo barbarian camp") + 1]
	local tribe = TRIBE_CAVALRY or TRIBE_MELEE
	local mgr = Game.GetBarbarianManager()
	local id = mgr:CreateTribeOfType(tribe.Index, p:GetIndex())
	if (id == nil or id < 0) and TRIBE_MELEE ~= nil and tribe ~= TRIBE_MELEE then
		id = mgr:CreateTribeOfType(TRIBE_MELEE.Index, p:GetIndex())
	end
	if id ~= nil and id >= 0 then
		mgr:CreateTribeUnits(id, "CLASS_MELEE", 1, p:GetIndex(), 0)
		print("ZhanguoV4: barbarian camp in " .. z.name .. " at (" .. p:GetX() .. "," .. p:GetY() .. ")")
	end
end

local function OnGameTurnStarted(turn)
	if turn < BARB_FIRST_TURN or (turn - BARB_FIRST_TURN) % BARB_INTERVAL ~= 0 then return end
	if Game.GetEras ~= nil and Game.GetEras():GetCurrentEra() > BARB_LAST_ERA then return end
	for _, z in ipairs(BARB_ZONES) do
		local ok, err = pcall(FillZone, z)
		if not ok then print("ZhanguoV4: barbarian zone " .. z.name .. " failed: " .. tostring(err)) end
	end
end

GameEvents.CityBuilt.Add(OnCityBuilt)
if CAMP ~= nil and GameInfo.BarbarianTribes ~= nil and not GameConfiguration.GetValue("GAME_NO_BARBARIANS") then
	GameEvents.OnGameTurnStarted.Add(OnGameTurnStarted)
end
print("ZhanguoV4 gameplay script loaded: " .. #SITES .. " city sites")
