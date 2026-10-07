#!/usr/bin/env python3
"""生成 month.html v2 —— 按猪哥认可的参考图重做外观。

设计规格（取色自 media/75b47ecf627248e983b3d13f7a67301d_image.png，实测非估算）：
  主红 #E22B37 / 日期红 #E1394A / 节气绿 #59A277 / 休标绿 #5B9B76 / 班标红 #D15562
  他月灰 #D5D5D5 / 农历字 #323232 / 底 纯白 #FFFFFF
关键形态：
  · 纯白底（不是深灰）+ 顶部实心红通栏
  · 无边框线，靠留白分隔
  · 休/班 = 右上角小圆角标（绿圆/红圆），不是文字标签
  · 节日与节气分色：节庆红、节气绿
  · 大号公历数字 + 小号农历
历法内核不动，复用 lunar.js 真算法 + 老黄历原生单日卡片。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<meta name="theme-color" content="#E22B37" />
<title>万年历 · 老黄历</title>
<link rel="manifest" href="manifest.json" />
<style>
  :root {
    --red:        #E22B37;   /* 顶栏 / 周六日 / 节庆 */
    --red-day:    #E1394A;   /* 日期红字 */
    --green:      #59A277;   /* 节气 */
    --green-badge:#5B9B76;   /* 休 角标 */
    --red-badge:  #D15562;   /* 班 角标 */
    --gray-other: #D5D5D5;   /* 他月日期 */
    --ink:        #323232;   /* 农历小字 */
    --ink-strong: #1A1A1A;   /* 公历数字 */
    --line:       #F0F0F0;
  }
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  html, body { margin: 0; padding: 0; background: #fff; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB",
                 "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
    color: var(--ink-strong);
    min-height: 100vh;
  }
  /* 内容容器：手机全宽，桌面居中限宽，否则格子会被拉散 */
  .app { max-width: 560px; margin: 0 auto; background: #fff; min-height: 100vh;
         box-shadow: 0 0 0 1px rgba(0,0,0,.04); }

  /* ---------- 顶部实心红通栏 ---------- */
  .topbar {
    background: var(--red); color: #fff;
    display: flex; align-items: center; justify-content: center;
    height: 52px; padding: 0 14px;
    position: sticky; top: 0; z-index: 20;
    width: 100%;
  }
  .topbar .title {
    font-size: 17px; font-weight: 600; letter-spacing: .5px;
    display: flex; align-items: center; gap: 4px; cursor: pointer;
    background: none; border: 0; color: #fff; font-family: inherit; padding: 6px 4px;
    white-space: nowrap; min-width: 0; overflow: hidden; text-overflow: ellipsis;
  }
  .topbar .title .caret { font-size: 11px; opacity: .9; }
  .topbar .side {
    position: absolute; top: 0; height: 52px; display: flex; align-items: center;
    gap: 14px; color: #fff; font-size: 20px;
  }
  .topbar .title-wrap {
    position: absolute; left: 50%; transform: translateX(-50%);
    display: flex; align-items: center; gap: 2px;
    max-width: calc(100% - 106px);
  }
  .topbar .mnav {
    flex: 0 0 auto; border: 0; background: transparent; color: #fff;
    font-size: 19px; line-height: 1; padding: 6px 8px; cursor: pointer;
    font-family: inherit; opacity: .92;
  }
  .topbar .mnav:active { opacity: .55; }
  .topbar .side.left { left: 14px; }
  .topbar .side.right { right: 14px; }
  .topbar .ico {
    background: none; border: 0; color: #fff; font-size: 19px;
    cursor: pointer; padding: 4px; line-height: 1; font-family: inherit;
  }
  .topbar .ico:active { opacity: .6; }

  /* ---------- 星期行 ---------- */
  .weekhead {
    display: grid; grid-template-columns: repeat(7, 1fr);
    padding: 10px 4px 6px; background: #fff;
    position: sticky; top: 52px; z-index: 19;
  }
  .weekhead span {
    text-align: center; font-size: 15px; color: #333; font-weight: 500;
  }
  .weekhead span.sun, .weekhead span.sat { color: var(--red); }

  /* ---------- 月网格：无边框，靠留白 ---------- */
  .grid {
    display: grid; grid-template-columns: repeat(7, 1fr);
    padding: 0 4px 20px; gap: 2px 0;
  }
  .cell {
    position: relative; background: #fff;
    min-height: 62px; padding: 7px 4px 6px;
    display: flex; flex-direction: column; align-items: center;
    cursor: pointer; user-select: none;
  }
  .cell:active { background: #F7F7F7; }
  .cell .d {
    font-size: 21px; font-weight: 500; line-height: 1.05;
    color: var(--ink-strong); font-variant-numeric: tabular-nums;
  }
  .cell.sun .d, .cell.sat .d { color: var(--red-day); }
  .cell .lun {
    font-size: 11px; line-height: 1.3; margin-top: 3px;
    color: var(--ink); white-space: nowrap;
  }
  /* 节日/节气分色 */
  .cell .lun.fest { color: var(--red); }
  .cell .lun.term { color: var(--green); }

  /* 他月日期：整体淡灰 */
  .cell.other .d, .cell.other .lun { color: var(--gray-other); }

  /* 今天：红色实心圆（参考图里今天是红色高亮） */
  .cell.today .d {
    color: #fff; background: var(--red);
    width: 34px; height: 34px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    margin: -1px 0 0; font-size: 19px; font-weight: 600;
  }
  .cell.today .lun { color: var(--red); font-weight: 600; }

  /* 休 / 班 右上角小圆角标 */
  .badge {
    position: absolute; top: 3px; right: 3px;
    width: 13px; height: 13px; border-radius: 3px;
    color: #fff; font-size: 9px; line-height: 13px; text-align: center;
    font-weight: 700; transform: scale(.92);
  }
  .badge.off  { background: var(--green-badge); }
  .badge.work { background: var(--red-badge); }

  /* ---------- 底部滑出详情面板（手机紧凑卡，参考国产日历 App 版式） ---------- */
  .mask {
    position: fixed; inset: 0; background: rgba(0,0,0,.45);
    opacity: 0; pointer-events: none; transition: opacity .22s; z-index: 40;
  }
  .mask.show { opacity: 1; pointer-events: auto; }
  .sheet {
    position: fixed; left: 50%; bottom: 0; z-index: 41;
    width: min(560px, 100vw);
    background: #fff; border-radius: 18px 18px 0 0;
    transform: translate(-50%, 102%);
    transition: transform .28s cubic-bezier(.22,.8,.28,1);
    max-height: 88vh; display: flex; flex-direction: column;
    box-shadow: 0 -6px 28px rgba(0,0,0,.16);
  }
  .sheet.show { transform: translate(-50%, 0); }
  .grabber { padding: 8px 0 2px; display: flex; justify-content: center; flex: 0 0 auto; }
  .grabber i { width: 38px; height: 4px; border-radius: 2px; background: #DCDCDC; display: block; }
  /* 手机竖屏（屏高足够时）详情不滚动 */
  @media (max-height: 900px) {
    .sheet { max-height: 94vh; }
  }
  /* 矮屏（iPhone SE 667 / 安卓 640）：进一步压缩，保证零滚动 */
  @media (max-height: 700px) {
    .sheet { max-height: 96vh; }
    .lun-hero { padding-bottom: 7px; }
    .lun-hero .big { font-size: 22px; }
    .lun-hero .ganzhi { margin-top: 3px; font-size: 12px; gap: 9px; }
    .yiji { padding: 6px 0 1px; }
    .yiji .items { font-size: 12.5px; line-height: 1.35; gap: 1px 7px; }
    .info-grid { margin-top: 6px; }
    .info-grid .cell { padding: 4px 5px; }
    .hours { margin-top: 6px; }
    .pengzu { margin-top: 6px; padding: 5px 9px; font-size: 11.5px; }
    .more-link { margin-top: 7px; padding: 7px 0; font-size: 12.5px; }
    .d-head { padding-bottom: 6px; }
    .d-nav { width: 27px; height: 27px; }
    .d-title b { font-size: 19px; }
  }
  .sheet-body {
    overflow-y: auto; overflow-x: hidden;
    padding: 0 16px 4px; -webkit-overflow-scrolling: touch; flex: 1 1 auto;
  }

  /* ---- 紧凑单日详情卡 ---- */
  /* 日期头：月日 + 星期 + 前后翻日 */
  .d-head {
    display: flex; align-items: center; justify-content: space-between;
    padding: 2px 0 8px; gap: 8px;
  }
  .d-nav {
    border: 0; background: #F4F4F4; color: #555; width: 30px; height: 30px;
    border-radius: 50%; font-size: 15px; line-height: 1; cursor: pointer;
    font-family: inherit; flex: 0 0 auto;
  }
  .d-nav:active { background: #E8E8E8; }
  .d-nav[disabled] { opacity: .3; }
  .d-title { text-align: center; flex: 1 1 auto; min-width: 0; }
  .d-title b { font-size: 22px; font-weight: 700; color: var(--ink-strong); letter-spacing: .5px; }
  .d-title span { font-size: 12px; color: #999; margin-left: 6px; }
  .d-sub { font-size: 12px; color: #888; margin-top: 3px; }

  /* 农历大标题（参考图核心：农历日放最大） */
  .lun-hero {
    text-align: center; padding: 0 0 10px;
    border-bottom: 1px solid #F2F2F2;
  }
  .lun-hero .big { font-size: 25px; font-weight: 700; color: #1A1A1A; letter-spacing: 1px; }
  .lun-hero .ganzhi {
    margin-top: 5px; font-size: 12.5px; color: #666;
    display: flex; justify-content: center; gap: 12px; flex-wrap: wrap;
  }
  .lun-hero .ganzhi em { font-style: normal; color: #444; }

  /* 节日横幅（详情卡顶部） */
  .fest-bar {
    text-align: center; margin: -2px 0 8px;
    font-size: 13px; font-weight: 600; color: var(--red);
    letter-spacing: .5px;
  }

  /* 宜忌 */
  .yiji { padding: 9px 0 2px; display: flex; gap: 9px; align-items: flex-start; }
  .yiji + .yiji { padding-top: 4px; }
  .yiji .tag {
    flex: 0 0 auto; width: 20px; height: 20px; border-radius: 50%;
    color: #fff; font-size: 12px; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
    font-family: "STKaiti", "KaiTi", serif; margin-top: 1px;
  }
  .yiji.yi .tag { background: var(--green); }
  .yiji.ji .tag { background: #B0B0B0; }
  .yiji .items {
    flex: 1 1 auto; display: flex; flex-wrap: wrap;
    gap: 2px 8px; font-size: 13.5px; color: #333; line-height: 1.45;
  }
  .yiji .items span { white-space: nowrap; }

  /* 信息格：五行/冲煞/值神 三栏 + 吉神方位 两栏 */
  .info-grid {
    display: grid; grid-template-columns: repeat(3, 1fr);
    border: 1px solid #EEE; border-radius: 10px;
    overflow: hidden; margin-top: 8px;
  }
  .info-grid .cell { padding: 6px 6px; text-align: center; }
  .info-grid .cell + .cell { border-left: 1px solid #EEE; }
  .info-grid .cell .k { font-size: 10.5px; color: #999; margin-bottom: 2px; }
  .info-grid .cell .v { font-size: 12.5px; color: #222; font-weight: 600; }

  .info-grid.two { grid-template-columns: repeat(2, 1fr); }
  .info-grid.two .cell:nth-child(3) { border-left: 0; }
  .info-grid.two .cell:nth-child(n+3) { border-top: 1px solid #EEE; }
  /* 四格一行（吉神方位） */
  .info-grid.four { grid-template-columns: repeat(4, 1fr); }
  .info-grid.four .cell { padding: 6px 2px; }
  .info-grid.four .cell .v { font-size: 12px; }

  /* 时辰宜忌小表 */
  .hours { margin-top: 8px; }
  .hours .cap { font-size: 10.5px; color: #999; margin-bottom: 3px; }
  .hours table { width: 100%; border-collapse: collapse; font-size: 10.5px; }
  .hours th, .hours td {
    border: 1px solid #EFEFEF; padding: 2.5px 1px; text-align: center;
    font-weight: 400; color: #555;
  }
  .hours th { background: #FAFAFA; color: #888; }
  .hours td.ok { color: var(--green); font-weight: 700; }
  .hours td.no { color: #C0392B; font-weight: 700; }

  /* 彭祖百忌 */
  .pengzu {
    margin-top: 8px; background: #FBFBFB; border-radius: 10px;
    padding: 7px 10px; font-size: 12px; color: #666; line-height: 1.55;
  }
  .pengzu b { color: #444; font-weight: 600; }

  /* 完整黄历入口 */
  .more-link {
    display: block; width: 100%; margin: 9px 0 2px;
    background: #fff; border: 1px solid #EEE; border-radius: 10px;
    padding: 8px 0; font-size: 13px; color: #666;
    cursor: pointer; font-family: inherit; text-align: center;
  }
  .more-link:active { background: #F7F7F7; }
  .more-link i { font-style: normal; color: #BBB; margin-left: 4px; }

  .quicknav {
    display: flex; gap: 8px; justify-content: center; flex: 0 0 auto;
    padding: 10px 16px calc(14px + env(safe-area-inset-bottom));
    background: #fff; border-top: 1px solid var(--line);
  }
  .quicknav button {
    flex: 1; max-width: 150px; background: #F7F7F7; border: 1px solid transparent;
    border-radius: 10px; padding: 10px 0; font-size: 14px; color: #333;
    cursor: pointer; font-family: inherit;
  }
  .quicknav button:active { background: #EFEFEF; }
  .quicknav button.primary { background: var(--red); border-color: var(--red); color: #fff; }

  /* ---------- 年月选择弹层 ---------- */
  .picker {
    position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 60;
    display: none; align-items: flex-start; justify-content: center; padding-top: 10vh;
  }
  .picker.show { display: flex; }
  .picker-card {
    background: #fff; border-radius: 16px; width: min(400px, 92vw);
    max-height: 76vh; overflow: hidden; display: flex; flex-direction: column;
  }
  .picker-card h3 { margin: 0; padding: 16px 16px 6px; font-size: 15px; color: #222; }
  .picker-grid { overflow-y: auto; padding: 4px 14px 14px; }

  /* 年份行：‹ 2026年 › */
  .pk-yrow {
    display: flex; align-items: center; justify-content: space-between;
    gap: 8px; padding: 4px 0 10px;
  }
  .pk-ylab {
    flex: 1 1 auto; text-align: center; font-size: 18px;
    font-weight: 700; color: var(--ink-strong);
  }
  .pk-arrow {
    flex: 0 0 auto; width: 34px; height: 34px; border-radius: 50%;
    background: #F4F4F4; border: 0; color: #555; font-size: 17px;
    line-height: 1; cursor: pointer; font-family: inherit;
  }
  .pk-arrow:active { background: #E8E8E8; }

  /* 年份快选条 */
  .pk-strip {
    display: grid; grid-template-columns: repeat(5, 1fr);
    gap: 6px; margin-bottom: 12px;
  }
  .pk-strip button {
    background: #F7F7F7; border: 0; border-radius: 8px; padding: 7px 0;
    font-size: 12.5px; color: #555; cursor: pointer; font-family: inherit;
  }
  .pk-strip button.cur { background: #FDECEE; color: var(--red); font-weight: 700; }

  /* 12 个月 */
  .pk-months {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
  }
  .pk-months button {
    background: #F5F5F5; border: 0; border-radius: 9px; padding: 11px 0;
    font-size: 14px; color: #333; cursor: pointer; font-family: inherit;
  }
  .pk-months button.cur {
    background: var(--red); color: #fff; font-weight: 700;
  }

  /* 确定 / 取消 */
  .pk-acts { display: flex; gap: 10px; margin-top: 16px; }
  .pk-acts button {
    flex: 1; border: 0; border-radius: 10px; padding: 12px 0;
    font-size: 15px; cursor: pointer; font-family: inherit;
  }
  .pk-no { background: #F4F4F4; color: #555; }
  .pk-ok { background: var(--red); color: #fff; font-weight: 600; }
  .pk-ok:active { opacity: .85; }
</style>
</head>
<body>

<div class="app">
<div class="topbar">
  <div class="side left">
    <button class="ico" id="btnToday" title="回到今天">◉</button>
  </div>
  <div class="title-wrap">
    <button class="mnav" id="btnPrevMonth" title="上个月">‹</button>
    <button class="title" id="btnPick">2026年10月<span class="caret">▼</span></button>
    <button class="mnav" id="btnNextMonth" title="下个月">›</button>
  </div>
  <div class="side right">
    <button class="ico" id="btnList" title="打开单日黄历页（可返回）">☰</button>
  </div>
</div>

<div class="weekhead">
  <span class="sun">日</span><span>一</span><span>二</span><span>三</span>
  <span>四</span><span>五</span><span class="sat">六</span>
</div>

<div class="grid" id="grid"></div>
</div>

<div class="mask" id="mask"></div>
<div class="sheet" id="sheet">
  <div class="grabber"><i></i></div>
  <div class="sheet-body" id="sheetBody"></div>
  <div class="quicknav">
    <button id="btnPrevDay">前一天</button>
    <button id="btnTodayIn">今天</button>
    <button id="btnNextDay">后一天</button>
  </div>
</div>

<div class="picker" id="picker">
  <div class="picker-card">
    <h3>选择年月</h3>
    <div class="picker-grid" id="pickerGrid"></div>
  </div>
</div>

<script src="./lunar.js"></script>
<script src="./calendar-art.js"></script>
<script>
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var today = new Date();
  var TY = today.getFullYear(), TM = today.getMonth() + 1, TD = today.getDate();
  var cur = { y: TY, m: TM };
  var HAS = !!(window.Solar && window.LunarUtil);
  var curDay = null;

  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function key(y, m, d) { return y + "-" + pad(m) + "-" + pad(d); }

  // 法定节假日 / 调休
  function holiday(y, m, d) {
    try {
      var h = window.HolidayUtil.getHoliday(y, m, d);
      if (!h) return null;
      var work = !!(h.isWork && h.isWork());
      return { name: h.getName(), work: work };
    } catch (e) { return null; }
  }

  // ---------- 公历节日表 ----------
  // lunar.js 内置的节日全是农历节日（春节/中秋等），公历节日一条都没有，
  // 所以这里自己补一份。键为 "月-日"。
  var SOLAR_FEST = {
    "1-1": "元旦",
    "2-14": "情人节",
    "3-8": "妇女节",
    "3-12": "植树节",
    "4-1": "愚人节",
    "5-1": "劳动节",
    "5-4": "青年节",
    "6-1": "儿童节",
    "7-1": "建党节",
    "8-1": "建军节",
    "9-10": "教师节",
    "10-1": "国庆节",
    "10-31": "万圣夜",
    "11-11": "双十一",
    "12-24": "平安夜",
    "12-25": "圣诞节"
  };

  // 农历节日取「主要」的那几个：lunar.js 的 getFestivals() 会返回一堆偏门节日
  // （尾牙/填仓节/分龙节…），全塞进格子里太吵，这里只留大众熟知的。
  var LUNAR_FEST_MAIN = {
    "除夕": 1, "春节": 1, "元宵节": 1, "端午节": 1, "七夕节": 1,
    "中元节": 1, "中秋节": 1, "重阳节": 1, "腊八节": 1
  };

  // 取当日农历节日（仅主要节日）
  function lunarFest(lu) {
    try {
      var f = lu.getFestivals() || [];
      for (var i = 0; i < f.length; i++) {
        if (LUNAR_FEST_MAIN[f[i]]) return f[i];
      }
    } catch (e) {}
    return null;
  }

  // ---------- 渲染月网格 ----------
  // 农历信息（供网格用）
  // 优先级：公历节日 > 农历大节 > 节气 > 普通农历日
  // （法定假期名与休/班角标由调用方在更外层优先处理）
  function lunarOf(y, m, d) {
    if (!HAS) return null;
    try {
      var so = window.Solar.fromYmd(y, m, d);
      var lu = so.getLunar();

      // 1) 公历节日（元旦/情人节/圣诞节…）
      var sf = SOLAR_FEST[m + "-" + d];
      if (sf) return { text: sf, type: "fest" };

      // 2) 农历大节（春节/中秋/端午…）
      var lf = lunarFest(lu);
      if (lf) return { text: lf, type: "fest" };

      // 3) 节气
      var t = lu.getJieQiTable();
      var names = ["冬至","小寒","大寒","立春","雨水","惊蛰","春分","清明","谷雨","立夏","小满","芒种",
                   "夏至","小暑","大暑","立秋","处暑","白露","秋分","寒露","霜降","立冬","小雪","大雪"];
      for (var i = 0; i < names.length; i++) {
        var jd = t[names[i]];
        if (jd && jd.getYear() === y && jd.getMonth() === m && jd.getDay() === d) {
          return { text: names[i], type: "term" };
        }
      }

      // 4) 普通农历日
      if (lu.getDay() === 1) return { text: lu.getMonthInChinese() + "月", type: "lunar" };
      return { text: lu.getDayInChinese(), type: "lunar" };
    } catch (e) { return null; }
  }

  // ---------- 渲染月网格 ----------
  function render(y, m) {
    cur.y = y; cur.m = m;
    $("btnPick").innerHTML = y + "年" + m + "月<span class='caret'>▼</span>";

    var grid = $("grid");
    grid.innerHTML = "";

    var firstDow = new Date(y, m - 1, 1).getDay();       // 0=日
    var dim = new Date(y, m, 0).getDate();
    var pdim = new Date(y, m - 1, 0).getDate();

    function cell(day, mm, yy, other) {
      var hol = other ? null : holiday(yy, mm, day);
      var c = document.createElement("div");
      c.className = "cell";
      var dow = new Date(yy, mm - 1, day).getDay();
      if (dow === 0) c.classList.add("sun");
      else if (dow === 6) c.classList.add("sat");
      if (other) c.classList.add("other");
      if (!other && yy === TY && mm === TM && day === TD) c.classList.add("today");

      var dEl = document.createElement("div");
      dEl.className = "d";
      dEl.textContent = day;
      c.appendChild(dEl);

      var lun = other ? null : lunarOf(yy, mm, day);
      var lunText = "", lunCls = "";
      // 显示优先级：节日/节气名 > 休/班。
      // 注意：法定假期名（如「春节」）只在节日当天显示，不能铺满整个假期区间，
      // 否则连着 9 天都写「春节」。区间内的其余日子回落成「休」角标即可。
      if (lun && (lun.type === "fest" || lun.type === "term")) {
        lunText = lun.text; lunCls = lun.type;
      } else if (hol && hol.name && !hol.work && !lun) {
        lunText = hol.name; lunCls = "fest";
      } else if (lun) {
        // 其余日子照常显示农历；「班」由上角标负责，不再重复写文字
        lunText = lun.text; lunCls = "";
      }
      if (lunText) {
        var lEl = document.createElement("div");
        lEl.className = "lun" + (lunCls ? " " + lunCls : "");
        lEl.textContent = lunText;
        c.appendChild(lEl);
      }

      // 休 / 班 角标
      if (hol) {
        var b = document.createElement("div");
        b.className = "badge " + (hol.work ? "work" : "off");
        b.textContent = hol.work ? "班" : "休";
        c.appendChild(b);
      }

      if (!other) c.addEventListener("click", function () { openDay(yy, mm, day); });
      return c;
    }

    // 上月补齐
    var lead = pdim - firstDow + 1;
    for (var i = 0; i < firstDow; i++) {
      var py = m === 1 ? y - 1 : y, pm = m === 1 ? 12 : m - 1;
      grid.appendChild(cell(lead + i, pm, py, true));
    }
    for (var d = 1; d <= dim; d++) grid.appendChild(cell(d, m, y, false));
    var tail = (7 - ((firstDow + dim) % 7)) % 7;
    for (var k = 1; k <= tail; k++) {
      var ny = m === 12 ? y + 1 : y, nm = m === 12 ? 1 : m + 1;
      grid.appendChild(cell(k, nm, ny, true));
    }
  }

  // ---------- 详情面板（紧凑单日卡，一屏放下） ----------
  var sheetCache = {};
  function openDay(y, m, d, skipSheet) {
    if (!HAS) return;
    curDay = { y: y, m: m, d: d };
    var so = window.Solar.fromYmd(y, m, d);
    var lu = so.getLunar();

    var body = $("sheetBody");
    body.innerHTML = "";
    body.appendChild(buildDayCard(so, lu, y, m, d));
    body.scrollTop = 0;

    if (!skipSheet) { $("mask").classList.add("show"); $("sheet").classList.add("show"); }
  }

  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt !== undefined && txt !== null) e.textContent = txt;
    return e;
  }

  // 取宜忌：只保留 ≤2 字的短语，最多 n 个
  function pick(arr, n) {
    var out = [];
    try { arr = arr || []; } catch (e) { arr = []; }
    for (var i = 0; i < arr.length && out.length < n; i++) {
      var t = String(arr[i] || "").trim();
      if (t && t.length <= 2) out.push(t);
    }
    return out;
  }

  function buildDayCard(so, lu, y, m, d) {
    var WK = ["日","一","二","三","四","五","六"];
    var frag = document.createDocumentFragment();

    // === 日期头（含前后翻日，省掉底部按钮占的竖向空间）===
    var head = el("div", "d-head");
    var bPrev = el("button", "d-nav", "‹");
    var bNext = el("button", "d-nav", "›");
    bPrev.onclick = function () { shiftDay(-1); };
    bNext.onclick = function () { shiftDay(1); };
    var tt = el("div", "d-title");
    tt.appendChild(el("b", null, (m) + "月" + d + "日"));
    tt.appendChild(el("span", null, "星期" + WK[so.getWeek()]));
    var bClose = el("button", "d-nav", "✕");
    bClose.id = "btnClose";
    bClose.onclick = function () { closeSheet(); };
    head.appendChild(bPrev); head.appendChild(tt); head.appendChild(bNext); head.appendChild(bClose);
    frag.appendChild(head);

    // === 节日横幅（有节日时显示在农历标题上方）===
    (function () {
      var names = [];
      var sf = SOLAR_FEST[m + "-" + d];
      if (sf) names.push(sf);
      var lf = lunarFest(lu);
      if (lf && lf !== sf) names.push(lf);
      if (!names.length) return;
      var bar = el("div", "fest-bar", names.join(" · "));
      frag.appendChild(bar);
    })();

    // === 农历主标题 ===
    var hero = el("div", "lun-hero");
    hero.appendChild(el("div", "big", lu.getMonthInChinese() + "月" + lu.getDayInChinese()));
    var gz = el("div", "ganzhi");
    gz.appendChild(el("em", null, lu.getYearInGanZhi() + "年"));
    gz.appendChild(el("em", null, lu.getMonthInGanZhi() + "月"));
    gz.appendChild(el("em", null, lu.getDayInGanZhi() + "日"));
    hero.appendChild(gz);
    frag.appendChild(hero);

    // === 节气 / 下一节气 ===
    (function () {
      var t = lu.getJieQiTable();
      var names = ["冬至","小寒","大寒","立春","雨水","惊蛰","春分","清明","谷雨","立夏","小满","芒种",
                   "夏至","小暑","大暑","立秋","处暑","白露","秋分","寒露","霜降","立冬","小雪","大雪"];
      var todayTerm = null, next = null;
      var sk = so.getYear() * 10000 + so.getMonth() * 100 + so.getDay();
      for (var i = 0; i < names.length; i++) {
        var jd = t[names[i]];
        if (!jd) continue;
        var jk = jd.getYear() * 10000 + jd.getMonth() * 100 + jd.getDay();
        if (jk === sk) todayTerm = names[i];
        if (!next && jk > sk) next = { name: names[i], jd: jd };
      }
      if (todayTerm) {
        var s = el("div", "d-sub", todayTerm + " · 今日节气");
        s.style.cssText = "text-align:center;color:#59A277;margin:-8px 0 10px;font-weight:600";
        frag.appendChild(s);
      } else if (next) {
        var s2 = el("div", "d-sub", "下一节气 " + next.name + " " + (next.jd.getMonth() + 1) + "月" + next.jd.getDay() + "日");
        s2.style.cssText = "text-align:center;color:#59A277;margin:-8px 0 10px";
        frag.appendChild(s2);
      }
    })();

    // === 宜 / 忌 ===
    function yijiRow(kind, label, words) {
      var row = el("div", "yiji " + kind);
      row.appendChild(el("div", "tag", label));
      var items = el("div", "items");
      if (!words.length) {
        var none = el("span", null, "无");
        none.style.color = "#AAA";
        items.appendChild(none);
      } else {
        words.forEach(function (w) { items.appendChild(el("span", null, w)); });
      }
      row.appendChild(items);
      return row;
    }
    var yi = pick(lu.getDayYi(1), 12);
    var ji = pick(lu.getDayJi(1), 8);
    frag.appendChild(yijiRow("yi", "宜", yi));
    frag.appendChild(yijiRow("ji", "忌", ji));

    // === 五行 / 冲煞 / 值神 ===
    var g1 = el("div", "info-grid");
    [["五行", lu.getDayNaYin()],
     ["冲煞", lu.getDayShengXiao() + "日冲" + lu.getDayChongShengXiao()],
     ["值神", lu.getZhiXing()]].forEach(function (p) {
      var c = el("div", "cell");
      c.appendChild(el("div", "k", p[0]));
      c.appendChild(el("div", "v", p[1]));
      g1.appendChild(c);
    });
    frag.appendChild(g1);

    // === 吉神方位（一行四格：省掉一整行高度）===
    var g2 = el("div", "info-grid four");
    [["财神", lu.getDayPositionCaiDesc()],
     ["福神", lu.getDayPositionFuDesc()],
     ["喜神", lu.getDayPositionXiDesc()],
     ["阳贵", lu.getDayPositionYangGuiDesc()]].forEach(function (p) {
      var c = el("div", "cell");
      c.appendChild(el("div", "k", p[0]));
      c.appendChild(el("div", "v", p[1]));
      g2.appendChild(c);
    });
    frag.appendChild(g2);

    // === 时辰宜忌（参考图同款一行）===
    // 注意：lunar.js 的 getTimeYi() 不接受参数，取的是「该 Lunar 对象自身的时辰」，
    // 必须用 Lunar.fromYmdHms 逐时辰构造，否则 12 个时辰会返回同一结果。
    (function () {
      var ZHI = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"];
      var HOUR = ["23~1","1~3","3~5","5~7","7~9","9~11","11~13","13~15","15~17","17~19","19~21","21~23"];
      var wrap = el("div", "hours");
      wrap.appendChild(el("div", "cap", "时辰宜忌"));
      var tb = el("table");
      var tr1 = el("tr"), tr2 = el("tr");
      tr1.appendChild(el("th", null, "时"));
      tr2.appendChild(el("th", null, "辰"));
      for (var i = 0; i < 12; i++) {
        var th = el("th", null, ZHI[i]);
        th.title = HOUR[i] + "时";
        tr1.appendChild(th);
        // 1,3,5...23 点分别为子~亥时；偶数点落在一个时辰的中段，避免边界歧义
        var ok = null;
        try {
          var l2 = window.Lunar.fromYmdHms(y, m, d, (1 + i * 2) % 24, 0, 0);
          var nYi = l2.getTimeYi().length, nJi = l2.getTimeJi().length;
          ok = nYi >= nJi;
        } catch (e) { ok = null; }
        tr2.appendChild(el("td", ok === null ? "" : (ok ? "吉" : "凶"),
                           ok === null ? "-" : (ok ? "吉" : "凶")));
      }
      tb.appendChild(tr1); tb.appendChild(tr2);
      wrap.appendChild(tb);
      frag.appendChild(wrap);
    })();

    // === 彭祖百忌 ===
    (function () {
      var txt = "";
      try { txt = lu.getPengZuGan() + " " + lu.getPengZuZhi(); } catch (e) {}
      if (!txt.trim()) return;
      var p = el("div", "pengzu");
      p.appendChild(el("b", null, "彭祖百忌 · "));
      p.appendChild(document.createTextNode(txt));
      frag.appendChild(p);
    })();

    // === 完整黄历入口 ===
    var more = el("button", "more-link");
    more.appendChild(document.createTextNode("查看完整黄历（八字 · 星宿 · 胎神）"));
    more.appendChild(el("i", null, "›"));
    more.onclick = function () { location.href = "./day.html"; };
    frag.appendChild(more);

    var box = el("div");
    box.appendChild(frag);
    return box;
  }


  function closeSheet() {
    $("mask").classList.remove("show");
    $("sheet").classList.remove("show");
  }

  // ---------- 年月选择 ----------
  // 年：左右翻页选任意年份（不再写死 8 个）；选完年就地刷新，不关闭面板，
  //     让「年 + 月」能在同一个面板里连续选完。
  var pkYear = null;      // 面板里当前正在编辑的年份
  var pkMonth = null;     // 面板里当前正在编辑的月份（未确认前不 render）

  function buildPicker() {
    pkYear = cur.y;
    pkMonth = cur.m;
    drawPicker();
  }

  function drawPicker() {
    var g = $("pickerGrid");
    g.innerHTML = "";

    // --- 年份行：‹  2026年  › ---
    var yRow = el("div", "pk-yrow");
    var yPrev = el("button", "pk-arrow", "‹");
    var yNext = el("button", "pk-arrow", "›");
    var yLab = el("div", "pk-ylab", pkYear + "年");
    yPrev.onclick = function () { pkYear--; drawPicker(); };
    yNext.onclick = function () { pkYear++; drawPicker(); };
    yRow.appendChild(yPrev); yRow.appendChild(yLab); yRow.appendChild(yNext);
    g.appendChild(yRow);

    // --- 年份快选条（以 pkYear 为中心）---
    var strip = el("div", "pk-strip");
    for (var i = -2; i <= 2; i++) {
      (function (yy) {
        var b = el("button", (yy === pkYear ? "cur" : ""), yy + "");
        b.onclick = function () { pkYear = yy; drawPicker(); };
        strip.appendChild(b);
      })(pkYear + i);
    }
    g.appendChild(strip);

    // --- 12 个月 ---
    var mGrid = el("div", "pk-months");
    for (var mm = 1; mm <= 12; mm++) {
      (function (v) {
        var cls = (v === pkMonth) ? "cur" : "";
        var b2 = el("button", cls, v + "月");
        b2.onclick = function () { pkMonth = v; drawPicker(); };
        mGrid.appendChild(b2);
      })(mm);
    }
    g.appendChild(mGrid);

    // --- 确定 / 取消 ---
    var acts = el("div", "pk-acts");
    var bOk = el("button", "pk-ok", "确定");
    var bNo = el("button", "pk-no", "取消");
    bOk.onclick = function () { render(pkYear, pkMonth); $("picker").classList.remove("show"); };
    bNo.onclick = function () { $("picker").classList.remove("show"); };
    acts.appendChild(bNo); acts.appendChild(bOk);
    g.appendChild(acts);
  }

  // ---------- 事件 ----------
  $("btnToday").onclick = function () { render(TY, TM); };
  $("btnList").onclick = function () { location.href = "./day.html"; };
  function stepMonth(n) {
    var nm = cur.m + n, ny = cur.y;
    if (nm < 1) { nm = 12; ny--; }
    if (nm > 12) { nm = 1; ny++; }
    render(ny, nm);
  }
  $("btnPrevMonth").onclick = function () { stepMonth(-1); };
  $("btnNextMonth").onclick = function () { stepMonth(1); };
  $("btnPick").onclick = function () { buildPicker(); $("picker").classList.add("show"); };
  $("picker").onclick = function (e) { if (e.target === $("picker")) $("picker").classList.remove("show"); };
  // 关闭按钮在详情卡内动态生成，这里不硬绑；仅绑常驻元素
  $("mask").onclick = closeSheet;
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeSheet(); });

  $("btnPrevDay").onclick = function () { shiftDay(-1); };
  $("btnNextDay").onclick = function () { shiftDay(1); };
  $("btnTodayIn").onclick = function () { openDay(TY, TM, TD); };
  function shiftDay(n) {
    if (!curDay) return;
    var dt = new Date(curDay.y, curDay.m - 1, curDay.d);
    dt.setDate(dt.getDate() + n);
    openDay(dt.getFullYear(), dt.getMonth() + 1, dt.getDate());
  }

  // 左右滑动切月
  (function () {
    var x0 = null, y0 = null;
    window.addEventListener("touchstart", function (e) {
      x0 = e.touches[0].clientX; y0 = e.touches[0].clientY;
    }, { passive: true });
    window.addEventListener("touchend", function (e) {
      if (x0 === null) return;
      var dx = e.changedTouches[0].clientX - x0;
      var dy = e.changedTouches[0].clientY - y0;
      x0 = null;
      if ($("sheet").classList.contains("show")) return;
      if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.6) {
        var nm = cur.m + (dx < 0 ? 1 : -1), ny = cur.y;
        if (nm < 1) { nm = 12; ny--; }
        if (nm > 12) { nm = 1; ny++; }
        render(ny, nm);
      }
    }, { passive: true });
  })();

  render(cur.y, cur.m);
})();
</script>
</body>
</html>
"""

HTML = HTML.replace("__CARD__", "")
(DIST / "index.html").write_text(HTML, encoding="utf-8")

# 旧地址 ./month.html 保留一个跳转页，避免已有书签/主屏图标失效
REDIRECT = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>老黄历 · 万年历</title>
<link rel="canonical" href="./">
<meta http-equiv="refresh" content="0; url=./">
<script>location.replace("./");</script>
</head>
<body style="margin:0;background:#fff;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif">
  <p style="text-align:center;padding:40px 20px;color:#888;font-size:14px">
    月视图已移到首页，正在跳转…<br>
    <a href="./" style="color:#E22B37">点这里如果没反应</a>
  </p>
</body>
</html>
"""
(DIST / "month.html").write_text(REDIRECT, encoding="utf-8")

print(f"dist/index.html  {len(HTML):,} B  (月视图，站点首页)")
print(f"dist/month.html  {len(REDIRECT):,} B  (跳转页 → ./)")
