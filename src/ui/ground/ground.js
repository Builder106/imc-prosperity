// The Intara section: four recorded days drawn as one cut face, a probe that opens the order
// book at any tick, and the legend that switches layers. GSAP is inlined ahead of this module
// by src/ui/ground.py into gsapScope, and its ticker is the only clock.

const gsap = gsapScope.window.gsap;
const DAYS = [-2, -1, 0, 1];
const TICKS = 10000;
const SPAN = DAYS.length * TICKS;
const GOODS = [
  { id: "INTARIAN_PEPPER_ROOT", key: "pepper", name: "Intarian Pepper Root", color: "#ee5a36" },
  { id: "ASH_COATED_OSMIUM", key: "osmium", name: "Ash-Coated Osmium", color: "#8ea9c6" },
];
const COLORS = { dust: "#e7e9ec", muted: "#959ca6", shelf: "#16181b", basalt: "#0d0e10" };
const MATCH_LABELS = { worse: "Beyond my quote", all: "At or beyond", none: "Never" };
const LEVELS = [
  ["Ask 3", 10, 11, "ask"], ["Ask 2", 8, 9, "ask"], ["Ask 1", 6, 7, "ask"],
  ["Bid 1", 0, 1, "bid"], ["Bid 2", 2, 3, "bid"], ["Bid 3", 4, 5, "bid"],
];

const nf = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
const fmt = (v) => (v < 0 ? "−" : "") + nf.format(Math.abs(v));
const signed = (v) => (v > 0 ? "+" : v < 0 ? "−" : "") + nf.format(Math.abs(v));
const dayName = (d) => (d < 0 ? `Day −${-d}` : `Day ${d}`);
const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const lerp = (a, b, t) => a + (b - a) * t;
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

const instances = new WeakMap();

export default function (component) {
  const { parentElement } = component;
  let inst = instances.get(parentElement);
  if (!inst) {
    inst = createSection(component);
    instances.set(parentElement, inst);
  }
  inst.update(component);
  return () => {
    // Streamlit calls this on unmount; a rerun keeps the same root, so only tear down when the
    // root has really left the page.
    setTimeout(() => {
      const host = parentElement.host || parentElement;
      if (!host.isConnected) {
        inst.destroy();
        instances.delete(parentElement);
      }
    }, 0);
  };
}

async function fetchText(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${response.status} for ${url}`);
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (bytes[0] === 0x1f && bytes[1] === 0x8b) {
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
    return new Response(stream).text();
  }
  return new TextDecoder().decode(bytes);
}

function parsePrices(text) {
  const goods = {};
  for (const g of GOODS) {
    goods[g.key] = { mid: new Float32Array(TICKS).fill(NaN), book: new Int32Array(TICKS * 12) };
  }
  const byId = Object.fromEntries(GOODS.map((g) => [g.id, goods[g.key]]));
  const lines = text.split("\n");
  for (let n = 1; n < lines.length; n++) {
    const c = lines[n].split(";");
    if (c.length < 16) continue;
    const series = byId[c[2]];
    if (!series) continue;
    const i = (+c[1] / 100) | 0;
    if (i < 0 || i >= TICKS) continue;
    const mid = +c[15];
    if (mid > 0) series.mid[i] = mid;
    for (let k = 0; k < 12; k++) series.book[i * 12 + k] = c[3 + k] ? Math.round(+c[3 + k]) : 0;
  }
  for (const g of GOODS) {
    const s = goods[g.key];
    let open = NaN, close = NaN, lo = Infinity, hi = -Infinity;
    for (let i = 0; i < TICKS; i++) {
      const v = s.mid[i];
      if (!(v > 0)) continue;
      if (Number.isNaN(open)) open = v;
      close = v;
      lo = Math.min(lo, v);
      hi = Math.max(hi, v);
    }
    Object.assign(s, { open, close, lo, hi });
  }
  return goods;
}

function parseTrades(text) {
  const trades = new Map();
  const lines = text.split("\n");
  for (let n = 1; n < lines.length; n++) {
    const c = lines[n].split(";");
    if (c.length < 7) continue;
    const good = GOODS.find((g) => g.id === c[3]);
    if (!good) continue;
    const i = (+c[0] / 100) | 0;
    if (!trades.has(i)) trades.set(i, []);
    trades.get(i).push({ good: good.key, price: +c[5], qty: +c[6] });
  }
  return trades;
}

function createSection(component) {
  const root = component.parentElement;
  const $ = (sel) => root.querySelector(sel);
  const el = $(".tt");
  const refs = {
    fact: $(".tt-fact"), lede: $(".tt-lede"), caption: $("#tt-section-caption"),
    plot: $(".tt-plot"), canvas: $(".tt-canvas"), yaxis: $(".tt-yaxis"), tags: $(".tt-tags"),
    probe: $(".tt-probe"), probeTime: $(".tt-probe__time"), days: $(".tt-days"),
    when: $(".tt-core__when"), goods: $(".tt-core__goods"), legend: $(".tt-legend"),
    trader: $(".tt-trader"), results: $(".tt-results"), loading: $(".tt-loading"),
  };
  const ctx = refs.canvas.getContext("2d");
  queueMicrotask(() => el.classList.add("is-live"));

  const api = { setStateValue: component.setStateValue, setTriggerValue: component.setTriggerValue };
  const st = {
    layer: null, data: null, days: null, trades: null, mids: null,
    win: { a: 0, b: SPAN }, split: 0, tl: 0, grow: 0, osm: 0,
    zoom: null, probe: 3 * TICKS + 5000, ghost: null, dragging: false,
    replay: null, replayKey: null, positions: null, settings: null, busy: false,
    w: 0, h: 0, dirty: true, inView: true, lastPulse: 0, placed: false, headKey: "",
  };

  // Buttons for each recorded day; positioned under their stretch of the section.
  const back = document.createElement("button");
  back.className = "tt-back";
  back.type = "button";
  back.hidden = true;
  back.innerHTML = "<span>All four days</span>";
  refs.days.append(back);
  const dayButtons = DAYS.map((d, idx) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "tt-day";
    b.setAttribute("aria-pressed", "false");
    b.innerHTML = `<span>${dayName(d)}</span><small>${d === 1 ? "Round 2" : "Round 1"}</small>`;
    b.addEventListener("click", () => {
      if (st.layer === "trader") choose("day", d);
      else if (strip()) {
        api.setStateValue("place", { zoom: d, day: d, t: 500000 });
        api.setTriggerValue("nav", "ground");
      } else zoomTo(st.zoom === idx ? null : idx, true);
    });
    refs.days.append(b);
    return b;
  });
  back.addEventListener("click", () => zoomTo(null, true));

  // --- Data -------------------------------------------------------------------------------
  // The probe's day loads first so the readout opens early on slow networks; the other days follow.
  async function load(base) {
    const first = (st.probe / TICKS) | 0;
    const order = [first, ...DAYS.map((_, i) => i).filter((i) => i !== first)];
    st.days = new Array(DAYS.length);
    st.trades = new Array(DAYS.length);
    try {
      for (const idx of order) {
        const d = DAYS[idx];
        const [day, trades] = await Promise.all([
          fetchText(new URL(`${base}prices_day_${d}.csv.gz`, document.baseURI)).then(parsePrices),
          fetchText(new URL(`${base}trades_day_${d}.csv.gz`, document.baseURI)).then(parseTrades),
        ]);
        st.days[idx] = day;
        st.trades[idx] = trades;
        const mids = st.mids || {};
        for (const g of GOODS) {
          if (!mids[g.key]) mids[g.key] = new Float32Array(SPAN).fill(NaN);
          mids[g.key].set(day[g.key].mid, idx * TICKS);
        }
        setMids(mids);
        el.classList.add("is-ready");
        if (!st.introStarted) intro();
        renderHead(false);
        renderCore();
      }
      st.complete = true;
    } catch (error) {
      refs.loading.textContent = `The record could not be opened (${error.message}). Reload the page to try again.`;
    }
  }
  const dayAt = (g) => st.days && st.days[(g / TICKS) | 0];

  // A light overview from Python (every 25th tick) draws the section before the full days arrive.
  function seedOverview(ov) {
    const mids = {};
    for (const g of GOODS) {
      const all = new Float32Array(SPAN).fill(NaN);
      ov[g.key].forEach((v, k) => { if (v > 0) all[k * ov.stride] = v; });
      mids[g.key] = all;
    }
    setMids(mids);
    intro();
  }

  function setMids(mids) {
    st.mids = mids;
    st.midsVersion = (st.midsVersion || 0) + 1;
    let lo = Infinity, hi = -Infinity;
    for (const g of GOODS) for (const v of mids[g.key]) { if (v > 0) { if (v < lo) lo = v; if (v > hi) hi = v; } }
    const pad = (hi - lo) * 0.04;
    st.shared = [lo - pad, hi + pad];
    el.classList.add("has-overview");
    st.dirty = true;
  }

  function intro() {
    st.introStarted = true;
    let seen = false;
    try { seen = sessionStorage.getItem("tt-intro") === "1"; sessionStorage.setItem("tt-intro", "1"); } catch { /* storage off */ }
    if (seen || reduced()) {
      st.grow = 1; st.osm = 1; st.dirty = true;
      return;
    }
    const tl = gsap.timeline({ onUpdate: () => { st.dirty = true; } });
    tl.to(st, { osm: 1, duration: 0.6, ease: "power3.out" })
      .to(st, { grow: 1, duration: 1.6, ease: "power2.inOut" }, 0.25);
  }

  // --- Geometry ---------------------------------------------------------------------------
  const strip = () => st.layer === "notes" || st.layer === "index";
  function frame() {
    const mobile = st.w < 900;
    const margin = mobile ? 16 : 40;
    return { L: margin + (mobile ? 50 : 64), R: st.w - margin, T: mobile ? 48 : 60, B: st.h - (mobile ? 44 : 52) };
  }

  function lanes() {
    const { T, B } = frame();
    const h = B - T;
    const trader = { pepper: [0, 0.34], osmium: [0.42, 0.7], trader: [0.8, 1] };
    const ground = { pepper: [0, 0.5], osmium: [0.6, 1], trader: [1, 1] };
    const out = {};
    for (const k of ["pepper", "osmium", "trader"]) {
      const a = lerp(ground[k][0], trader[k][0], st.tl);
      const b = lerp(ground[k][1], trader[k][1], st.tl);
      out[k] = [T + a * h, T + b * h];
    }
    return out;
  }

  const sharedRange = () => st.shared;

  function laneRange(key) {
    const mids = st.mids[key];
    const a = Math.max(0, Math.floor(st.win.a)), b = Math.min(SPAN, Math.ceil(st.win.b));
    let lo = Infinity, hi = -Infinity;
    for (let g = a; g < b; g++) { const v = mids[g]; if (v > 0) { if (v < lo) lo = v; if (v > hi) hi = v; } }
    if (!Number.isFinite(lo)) return [9990, 10010];
    const pad = Math.max((hi - lo) * 0.12, 6);
    return [lo - pad, hi + pad];
  }

  function makeY(key, shared, lane) {
    const { T, B } = frame();
    const [slo, shi] = shared;
    const [llo, lhi] = laneRange(key);
    const [lt, lb] = lane;
    const s = st.split;
    return (p) => lerp(T + ((shi - p) / (shi - slo)) * (B - T), lt + ((lhi - p) / (lhi - llo)) * (lb - lt), s);
  }

  const xOf = (g) => { const { L, R } = frame(); return L + ((g - st.win.a) / (st.win.b - st.win.a)) * (R - L); };
  const gOf = (x) => { const { L, R } = frame(); return clamp(Math.round(st.win.a + ((x - L) / (R - L)) * (st.win.b - st.win.a)), Math.ceil(st.win.a), Math.floor(st.win.b) - 1); };

  // --- Drawing ----------------------------------------------------------------------------
  function resize() {
    const r = refs.plot.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    st.w = r.width; st.h = r.height;
    refs.canvas.width = Math.round(r.width * dpr);
    refs.canvas.height = Math.round(r.height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    st.dirty = true;
  }

  let colCache = new Map();
  function columns(series, y, key) {
    const stamp = `${key}|${st.w}|${st.h}|${st.win.a}|${st.win.b}|${st.split}|${st.tl}|${st.midsVersion}`;
    const hit = colCache.get(key);
    if (hit && hit.stamp === stamp) return hit.cols;
    const cols = buildColumns(series, y);
    colCache.set(key, { stamp, cols });
    return cols;
  }

  function buildColumns(series, y) {
    const { L, R } = frame();
    const cols = [];
    const span = st.win.b - st.win.a;
    for (let x = L; x < R; x++) {
      const g0 = Math.max(0, Math.floor(st.win.a + ((x - L) / (R - L)) * span));
      const g1 = Math.min(SPAN, Math.max(g0 + 1, Math.floor(st.win.a + ((x + 1 - L) / (R - L)) * span)));
      let lo = Infinity, hi = -Infinity, sum = 0, n = 0;
      for (let g = g0; g < g1; g++) {
        const v = series[g];
        if (!(v > 0)) continue;
        if (v < lo) lo = v;
        if (v > hi) hi = v;
        sum += v;
        n++;
      }
      cols.push(n ? { x, g: g0, lo: y(lo), hi: y(hi), mid: y(sum / n) } : null);
    }
    return cols;
  }

  function drawLine(cols, color, width, alpha, limitX) {
    ctx.globalAlpha = alpha;
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.lineJoin = "round";
    ctx.beginPath();
    let pen = false;
    for (const c of cols) {
      if (!c || c.x > limitX) { pen = false; continue; }
      if (pen) ctx.lineTo(c.x, c.mid); else ctx.moveTo(c.x, c.mid);
      pen = true;
    }
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  function draw() {
    const { L, R, T, B } = frame();
    ctx.clearRect(0, 0, st.w, st.h);
    if (!st.mids) return;
    const shared = sharedRange();
    const ln = lanes();
    const span = st.win.b - st.win.a;
    const perPx = span / (R - L);
    const growX = L + st.grow * (R - L);
    const ys = {};

    // Day boundaries: the joints of the section.
    ctx.strokeStyle = "rgba(231,233,236,0.08)";
    ctx.lineWidth = 1;
    for (let d = 1; d < DAYS.length; d++) {
      const x = Math.round(xOf(d * TICKS)) + 0.5;
      if (x > L && x < R) { ctx.beginPath(); ctx.moveTo(x, T - 24); ctx.lineTo(x, B + 18); ctx.stroke(); }
    }

    for (const g of GOODS) {
      const y = makeY(g.key, shared, ln[g.key]);
      ys[g.key] = y;
      const alpha = g.key === "osmium" ? st.osm : 1;
      const limit = g.key === "pepper" ? growX : R;
      if (alpha <= 0) continue;

      // Book strata: three asks above the mid, three bids below, while each pixel holds few ticks.
      const strata = clamp((60 - perPx) / 40, 0, 1) * st.split;
      if (strata > 0 && st.days) {
        for (let x = L; x < Math.min(R, limit); x += 1) {
          const gi = Math.floor(st.win.a + ((x + 0.5 - L) / (R - L)) * span);
          if (gi < 0 || gi >= SPAN) continue;
          const loaded = st.days[(gi / TICKS) | 0];
          if (!loaded) continue;
          const day = loaded[g.key];
          const o = (gi % TICKS) * 12;
          const b1 = day.book[o], b3 = day.book[o + 4] || day.book[o + 2] || b1;
          const a1 = day.book[o + 6], a3 = day.book[o + 10] || day.book[o + 8] || a1;
          ctx.fillStyle = g.color;
          if (a1) { ctx.globalAlpha = 0.3 * strata * alpha; const y1 = y(a1), y3 = y(a3); ctx.fillRect(x, Math.min(y1, y3) - 1, 1, Math.abs(y1 - y3) + 2); }
          if (b1) { ctx.globalAlpha = 0.17 * strata * alpha; const y1 = y(b1), y3 = y(b3); ctx.fillRect(x, Math.min(y1, y3) - 1, 1, Math.abs(y1 - y3) + 2); }
        }
        ctx.globalAlpha = 1;
      }

      const cols = columns(st.mids[g.key], y, g.key);
      ctx.fillStyle = g.color;
      ctx.globalAlpha = 0.35 * alpha;
      for (const c of cols) if (c && c.x <= limit) ctx.fillRect(c.x, c.hi, 1, Math.max(1, c.lo - c.hi));
      const seam = g.key === "osmium" ? lerp(3, 1.5, st.split) : 2;
      drawLine(cols, g.color, seam, alpha, limit);
      g.cols = cols;
    }

    // The root's growing tip during the intro.
    if (st.grow < 1) {
      const c = GOODS[0].cols?.filter((k) => k && k.x <= growX).pop();
      if (c) { ctx.fillStyle = GOODS[0].color; ctx.beginPath(); ctx.arc(c.x, c.mid, 4, 0, Math.PI * 2); ctx.fill(); }
    }

    // Idle: the root's tip breathes, and a faint pulse climbs the root every five seconds, like sap.
    if (st.grow >= 1 && !reduced() && GOODS[0].cols && !strip()) {
      const tip = GOODS[0].cols.filter(Boolean).pop();
      const breath = 0.5 + 0.5 * Math.sin(gsap.ticker.time * 2.1);
      ctx.globalAlpha = 0.25 + 0.35 * breath;
      ctx.fillStyle = GOODS[0].color;
      ctx.beginPath(); ctx.arc(tip.x, tip.mid, 4 + 3 * breath, 0, Math.PI * 2); ctx.fill();
      ctx.globalAlpha = 1;
    }
    const pulse = pulsePhase();
    if (pulse !== null && GOODS[0].cols) {
      const cols = GOODS[0].cols;
      const head = L + pulse * (R - L);
      ctx.lineCap = "round";
      for (let i = 0; i < cols.length; i++) {
        const c = cols[i], p = cols[i - 1];
        if (!c || !p || c.x > head || c.x < head - 90) continue;
        ctx.globalAlpha = 0.9 * (1 - (head - c.x) / 90);
        ctx.strokeStyle = "#ffb199";
        ctx.lineWidth = 3;
        ctx.beginPath(); ctx.moveTo(p.x, p.mid); ctx.lineTo(c.x, c.mid); ctx.stroke();
      }
      ctx.globalAlpha = 1;
      ctx.lineCap = "butt";
    }

    // The Trader's stratum and fills.
    if (st.replay && st.tl > 0.01) drawTrader(ys, ln.trader);

    drawCore(ys);
    placeOverlays(ys, ln, shared);
  }

  function drawTrader(ys, lane) {
    const { L, R } = frame();
    const rep = st.replay;
    const off = DAYS.indexOf(rep.day) * TICKS;
    const eq = rep.equitySeries;
    let lo = 0, hi = 0;
    for (const v of eq) { if (v < lo) lo = v; if (v > hi) hi = v; }
    const pad = (hi - lo) * 0.1 || 1;
    lo -= pad; hi += pad;
    const [lt, lb] = lane;
    const y = (v) => lb - ((v - lo) / (hi - lo)) * (lb - lt);
    const span = st.win.b - st.win.a;
    ctx.globalAlpha = st.tl;
    const zero = y(0);
    ctx.strokeStyle = "rgba(231,233,236,0.18)";
    ctx.setLineDash([2, 4]);
    ctx.beginPath(); ctx.moveTo(L, zero); ctx.lineTo(R, zero); ctx.stroke();
    ctx.setLineDash([]);
    ctx.beginPath();
    let first = null, last = null;
    for (let x = L; x < R; x++) {
      const gi = Math.floor(st.win.a + ((x - L) / (R - L)) * span) - off;
      if (gi < 0 || gi >= eq.length) continue;
      const yy = y(eq[gi]);
      if (first === null) { ctx.moveTo(x, yy); first = x; } else ctx.lineTo(x, yy);
      last = x;
    }
    ctx.strokeStyle = COLORS.dust;
    ctx.lineWidth = 1.5;
    ctx.stroke();
    if (first !== null) {
      ctx.lineTo(last, zero); ctx.lineTo(first, zero); ctx.closePath();
      ctx.fillStyle = "rgba(231,233,236,0.07)";
      ctx.fill();
    }
    // Fills: buys tick up from under the line, sells tick down from above it.
    ctx.strokeStyle = COLORS.dust;
    ctx.lineWidth = 1;
    // One mark per pixel column and side, so a busy stretch reads as density, not a smear.
    ctx.globalAlpha = 0.6 * st.tl;
    ctx.beginPath();
    const drawn = new Set();
    for (const [ts, key, qty] of rep.marks) {
      const g = off + ts / 100;
      if (g < st.win.a || g > st.win.b) continue;
      const mid = st.mids[key][g];
      if (!(mid > 0)) continue;
      const x = Math.round(xOf(g)) + 0.5;
      const slot = `${key}${x}${qty > 0}`;
      if (drawn.has(slot)) continue;
      drawn.add(slot);
      const yy = ys[key](mid);
      if (qty > 0) { ctx.moveTo(x, yy + 11); ctx.lineTo(x, yy + 6); } else { ctx.moveTo(x, yy - 11); ctx.lineTo(x, yy - 6); }
    }
    ctx.stroke();
    ctx.globalAlpha = 1;
    st.traderY = y;
  }

  function drawCore(ys) {
    const g = st.ghost ?? st.probe;
    const x = xOf(g);
    const day = dayAt(g);
    if (!day) return;
    const o = (g % TICKS) * 12;
    const zoomed = st.split > 0.5;
    for (const good of GOODS) {
      const s = day[good.key];
      const y = ys[good.key];
      ctx.fillStyle = good.color;
      if (zoomed) {
        for (const [, p, v, side] of LEVELS) {
          const price = s.book[o + p], vol = s.book[o + v];
          if (!price) continue;
          const len = Math.min(70, 6 + vol * 2.2);
          ctx.globalAlpha = side === "ask" ? 0.95 : 0.6;
          const yy = Math.round(y(price)) - 1.5;
          if (side === "ask") ctx.fillRect(x + 7, yy, len, 3); else ctx.fillRect(x - 7 - len, yy, len, 3);
        }
        ctx.globalAlpha = 1;
      }
      const mid = s.mid[g % TICKS];
      if (mid > 0) {
        ctx.beginPath(); ctx.arc(x, y(mid), 5, 0, Math.PI * 2);
        ctx.fillStyle = COLORS.shelf; ctx.fill();
        ctx.lineWidth = 2.5; ctx.strokeStyle = good.color; ctx.stroke();
      }
    }
  }

  function placeOverlays(ys, ln, shared) {
    const { L, R } = frame();
    // Probe.
    const g = st.ghost ?? st.probe;
    const px = xOf(g);
    refs.probe.style.translate = `${px}px 0`;
    refs.probe.classList.toggle("is-flipped", px > st.w - 220);
    refs.probe.classList.toggle("is-ghost", st.ghost !== null);
    refs.probeTime.textContent = `${dayName(DAYS[(g / TICKS) | 0])}, ${nf.format((g % TICKS) * 100)}`;

    // Price labels: shared scale before the split, each good's own scale after it.
    const labels = [];
    if (st.split < 0.5) {
      for (let p = 10000; p <= 14000; p += strip() ? 4000 : 2000) labels.push([ys.osmium(p), fmt(p)]);
    } else {
      for (const good of GOODS) {
        const [lo, hi] = laneRange(good.key);
        const step = niceStep((hi - lo) / 3);
        for (let p = Math.ceil(lo / step) * step; p <= hi; p += step) labels.push([ys[good.key](p), fmt(p)]);
      }
    }
    refs.yaxis.innerHTML = labels.map(([y, t]) => `<span style="top:${y.toFixed(1)}px">${t}</span>`).join("");

    // Tags at each line's right end.
    const tags = [];
    for (const good of strip() ? [] : GOODS) {
      const last = good.cols?.filter(Boolean).pop();
      if (!last) continue;
      let note;
      if (st.zoom === null || !st.days?.[st.zoom]) note = good.key === "pepper" ? "about +1,000 a day" : "near 10,000 every day";
      else {
        const s = st.days[st.zoom][good.key];
        note = good.key === "pepper" ? `${signed(s.close - s.open)} on the day` : `between ${fmt(s.lo)} and ${fmt(s.hi)}`;
      }
      const show = good.key === "pepper" ? st.grow >= 1 : st.osm >= 1;
      tags.push(`<span class="tt-tag tt-tag--${good.key}" style="top:${(last.mid - 8).toFixed(1)}px;opacity:${show ? 1 : 0}">${good.name}<small>${note}</small></span>`);
    }
    if (st.replay && st.tl > 0.5) {
      const [lt] = ln.trader;
      tags.push(`<span class="tt-tag tt-tag--trader" style="top:${(lt + 12).toFixed(1)}px">Your Trader<small>P&amp;L marked to the mid</small></span>`);
    }
    refs.tags.innerHTML = tags.join("");

    // Day buttons follow their stretch.
    dayButtons.forEach((b, idx) => {
      const a = Math.max(L, xOf(idx * TICKS)), z = Math.min(R, xOf((idx + 1) * TICKS));
      b.style.left = `${(a + z) / 2}px`;
      b.classList.toggle("is-away", z - a < 60);
      b.setAttribute("aria-pressed", String(st.zoom === idx));
    });
    back.hidden = st.zoom === null || st.layer === "trader";

    // The slider's own description.
    const day = dayAt(g);
    if (!day) return;
    const i = g % TICKS;
    const parts = GOODS.map((good) => { const m = day[good.key].mid[i]; return `${good.name} ${m > 0 ? fmt(m) : "no quote"}`; });
    refs.probe.setAttribute("aria-valuemin", String(Math.ceil(st.win.a)));
    refs.probe.setAttribute("aria-valuemax", String(Math.floor(st.win.b) - 1));
    refs.probe.setAttribute("aria-valuenow", String(st.probe));
    refs.probe.setAttribute("aria-valuetext", `${dayName(DAYS[(g / TICKS) | 0])}, timestamp ${nf.format(i * 100)}. ${parts.join(". ")}.`);
  }

  function niceStep(raw) {
    const p = 10 ** Math.floor(Math.log10(raw));
    const n = raw / p;
    return (n < 1.5 ? 1 : n < 3.5 ? 2 : n < 7.5 ? 5 : 10) * p;
  }

  function pulsePhase() {
    if (reduced() || st.grow < 1 || !st.inView || document.hidden || st.layer === "notes" || st.layer === "index") return null;
    const t = (gsap.ticker.time % 5) / 2.6;
    return t <= 1 ? t : null;
  }

  // --- Readout ----------------------------------------------------------------------------
  function renderCore() {
    const g = st.ghost ?? st.probe;
    const dIdx = (g / TICKS) | 0;
    const i = g % TICKS;
    const day = dayAt(g);
    if (!day) {
      refs.when.textContent = `Loading ${dayName(DAYS[dIdx]).toLowerCase()}`;
      return;
    }
    const trades = st.trades[dIdx].get(i) || [];
    let when = `${dayName(DAYS[dIdx])} at timestamp <b>${nf.format(i * 100)}</b>`;
    const rep = st.replay && st.layer === "trader" && replayOnDay(dIdx) ? st.replay : null;
    if (rep) when += `. Trader P&amp;L here: <b>${signed(rep.equitySeries[i] ?? 0)}</b>`;
    refs.when.innerHTML = when;
    refs.goods.innerHTML = GOODS.map((good) => {
      const s = day[good.key];
      const o = i * 12;
      const mid = s.mid[i];
      const rows = LEVELS.map(([label, p, v, side], k) => {
        const price = s.book[o + p], vol = s.book[o + v];
        const gap = k === 3 ? spreadRow(s.book[o], s.book[o + 6]) : "";
        const cell = price ? `<td class="tt-px">${fmt(price)}</td><td><span class="tt-bar" style="width:${Math.min(120, 4 + vol * 3)}px"></span>${vol}</td>` : `<td class="tt-none" colspan="2">No quote</td>`;
        return `${gap}<tr class="is-${side}"><th scope="row">${label}</th>${cell}</tr>`;
      }).join("");
      const mine = trades.filter((t) => t.good === good.key);
      const tape = mine.length ? `Public trades at this tick: ${mine.map((t) => `${t.qty} at ${fmt(t.price)}`).join(", ")}` : "No public trades at this tick";
      let note = mid > 0 ? `${signed(mid - s.open)} since the day opened at ${fmt(s.open)}` : "No mid price recorded at this tick";
      if (rep) note += `. Position ${signed(st.positions[good.key][i] || 0)}`;
      return `<article class="tt-good tt-good--${good.key}">
        <h3 class="tt-good__name">${good.name}</h3>
        <p class="tt-good__mid">${mid > 0 ? fmt(mid) : "No quote"}</p>
        <p class="tt-good__note">${note}</p>
        <table class="tt-ladder"><caption class="tt-visually-hidden">${good.name} order book</caption><tbody>${rows}</tbody></table>
        <p class="tt-good__trades">${tape}</p>
      </article>`;
    }).join("");
  }

  function replayOnDay(dIdx) { return st.replay && DAYS.indexOf(st.replay.day) === dIdx; }

  function spreadRow(bid, ask) {
    const text = bid && ask ? `Spread ${fmt(ask - bid)}` : "One side of the book is empty";
    return `<tr class="tt-gap"><th scope="row" colspan="3">${text}</th></tr>`;
  }

  // --- Header ----------------------------------------------------------------------------
  function headCopy() {
    const layer = st.layer;
    if (layer === "notes") return ["Field notes", "Questions go to the Prosperity 4 wiki, the recorded market and the code examples. Every answer lists the passages it used."];
    if (layer === "index") return ["Index", "Every recorded day and every layer of the section, as plain links."];
    if (layer === "trader") {
      const s = st.settings;
      if (!st.replay || st.busy) return [`Running the Round ${s.trader} Trader through ${dayName(s.day).toLowerCase()}.`, "Replaying every recorded tick of the day against the book and the public trades."];
      const r = st.replay;
      const verb = r.total_pnl >= 0 ? "made" : "lost";
      return [`Round ${r.trader} Trader, ${dayName(r.day).toLowerCase()}: ${verb} <em>${fmt(Math.abs(r.total_pnl))}</em>.`, `Replayed against all ${nf.format(r.equitySeries.length)} ticks of the recorded day, in XIRECs. White marks on each good are its fills, and the white stratum is its P&amp;L, marked to the last mid price.`];
    }
    if (st.zoom !== null) {
      const d = DAYS[st.zoom];
      const loaded = st.days?.[st.zoom];
      const summary = st.data?.zoom_summary?.day === d ? st.data.zoom_summary.goods : null;
      const p = loaded?.pepper || summary?.INTARIAN_PEPPER_ROOT;
      const o = loaded?.osmium || summary?.ASH_COATED_OSMIUM;
      if (p && o) {
        const low = o.lo ?? o.low, high = o.hi ?? o.high;
        return [`${dayName(d)}: the <em>root</em> climbed ${fmt(p.close - p.open)}.`, `Intarian Pepper Root went from <strong>${fmt(p.open)}</strong> to <strong>${fmt(p.close)}</strong> XIRECs. Ash-Coated Osmium stayed between <strong>${fmt(low)}</strong> and <strong>${fmt(high)}</strong>. Move the probe to read the order book at any tick.`];
      }
    }
    return ["Both goods opened at 10,000. Only the <em>root</em> grew.", "Four recorded days on Intara, the Prosperity 4 trading planet. <strong>Ash-Coated Osmium</strong> held near 10,000 XIRECs every day. <strong>Intarian Pepper Root</strong> climbed about 1,000 a day. Move the probe to open the order book at any tick."];
  }

  function renderHead(animate) {
    const [fact, lede] = headCopy();
    const key = fact + lede;
    if (key === st.headKey) return;
    st.headKey = key;
    refs.fact.innerHTML = fact;
    refs.lede.innerHTML = lede;
    const zoomText = st.zoom === null ? "all four recorded days" : dayName(DAYS[st.zoom]);
    refs.caption.textContent = `Price section of ${zoomText}: Intarian Pepper Root and Ash-Coated Osmium mid prices with their order books${st.layer === "trader" ? ", plus the Trader's fills and P&L" : ""}.`;
    if (animate && !reduced()) {
      gsap.fromTo([refs.fact, refs.lede], { y: 14, opacity: 0 }, { y: 0, opacity: 1, duration: 0.5, ease: "power3.out", stagger: 0.06, overwrite: true });
    }
  }

  // --- Zoom and probe -----------------------------------------------------------------------
  function zoomTo(idx, user) {
    st.zoom = idx;
    st.ghost = null;
    const target = idx === null ? { a: 0, b: SPAN } : { a: idx * TICKS, b: (idx + 1) * TICKS };
    if (idx !== null && (st.probe < target.a || st.probe >= target.b)) st.probe = target.a + TICKS / 2;
    const split = idx === null ? 0 : 1;
    if (reduced()) {
      Object.assign(st.win, target); st.split = split; st.dirty = true;
    } else {
      gsap.to(st.win, { ...target, duration: 0.9, ease: "expo.inOut", overwrite: true, onUpdate: () => { st.dirty = true; } });
      gsap.to(st, { split, duration: 0.7, delay: idx === null ? 0 : 0.15, ease: "power3.inOut", overwrite: "auto", onUpdate: () => { st.dirty = true; } });
    }
    renderHead(true);
    renderCore();
    if (user) commit();
  }

  function setProbe(g, user) {
    st.probe = clamp(g, Math.ceil(st.win.a), Math.floor(st.win.b) - 1);
    st.dirty = true;
    renderCore();
    if (user) scheduleCommit();
  }

  let commitTimer = 0;
  function scheduleCommit() { clearTimeout(commitTimer); commitTimer = setTimeout(commit, 600); }
  function commit() {
    clearTimeout(commitTimer);
    const dIdx = (st.probe / TICKS) | 0;
    api.setStateValue("place", { zoom: st.zoom === null ? null : DAYS[st.zoom], day: DAYS[dIdx], t: (st.probe % TICKS) * 100 });
  }

  const local = (e) => e.clientX - refs.plot.getBoundingClientRect().left;
  function onDown(e) {
    if (!st.mids || e.button > 0) return;
    st.dragging = true;
    refs.plot.setPointerCapture(e.pointerId);
    st.ghost = null;
    setProbe(gOf(local(e)), false);
  }
  function onMove(e) {
    if (!st.mids) return;
    if (st.dragging) { setProbe(gOf(local(e)), false); return; }
    if (e.pointerType === "mouse") { st.ghost = gOf(local(e)); st.dirty = true; renderCore(); }
  }
  function onUp() {
    if (!st.dragging) return;
    st.dragging = false;
    commit();
  }
  function onLeave() { if (st.ghost !== null) { st.ghost = null; st.dirty = true; renderCore(); } }
  function onKey(e) {
    const step = { ArrowLeft: -1, ArrowRight: 1, PageDown: -100, PageUp: 100 }[e.key];
    if (step !== undefined) {
      e.preventDefault();
      setProbe(st.probe + step * (e.shiftKey ? 10 : 1), true);
    } else if (e.key === "Home" || e.key === "End") {
      e.preventDefault();
      setProbe(e.key === "Home" ? st.win.a : st.win.b - 1, true);
    } else if (e.key === "Escape" && st.zoom !== null && st.layer !== "trader") {
      zoomTo(null, true);
    }
  }
  refs.plot.addEventListener("pointerdown", onDown);
  refs.plot.addEventListener("pointermove", onMove);
  refs.plot.addEventListener("pointerup", onUp);
  refs.plot.addEventListener("pointercancel", onUp);
  refs.plot.addEventListener("pointerleave", onLeave);
  refs.probe.addEventListener("keydown", onKey);

  // Layer links: real hrefs for new tabs, a trigger for in-place switches.
  function onNav(e) {
    const a = e.target.closest("[data-nav]");
    if (!a || e.metaKey || e.ctrlKey || e.shiftKey || e.button > 0) return;
    e.preventDefault();
    api.setTriggerValue("nav", a.dataset.nav);
  }
  el.addEventListener("click", onNav);

  // Trader choices.
  function renderChoices(options) {
    const s = st.settings;
    const groups = {
      trader: options.traders.map((r) => [r, `Round ${r} Trader`]),
      day: DAYS.map((d) => [d, dayName(d)]),
      match: options.matches.map((m) => [m, MATCH_LABELS[m]]),
    };
    for (const [name, items] of Object.entries(groups)) {
      const set = refs.trader.querySelector(`[data-choice="${name}"]`);
      const legend = set.querySelector("legend").outerHTML;
      set.innerHTML = legend + items.map(([v, label]) => `<button type="button" data-value="${v}" aria-pressed="${String(s[name]) === String(v)}">${label}</button>`).join("");
    }
  }
  function choose(name, value) {
    if (!st.settings || st.settings[name] === value) return;
    st.settings = { ...st.settings, [name]: value };
    st.busy = true;
    refs.trader.classList.add("is-busy");
    for (const btn of refs.trader.querySelectorAll(`[data-choice="${name}"] button`)) {
      btn.setAttribute("aria-pressed", String(btn.dataset.value === String(value)));
    }
    if (name === "day") zoomTo(DAYS.indexOf(value), false);
    renderHead(true);
    api.setStateValue("replay", st.settings);
  }
  refs.trader.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-value]");
    if (!b) return;
    const name = b.closest("[data-choice]").dataset.choice;
    choose(name, name === "match" ? b.dataset.value : Number(b.dataset.value));
  });

  function renderResults() {
    const r = st.replay;
    if (!r) { refs.results.innerHTML = ""; return; }
    const pnl = r.product_pnl;
    const cells = [
      ["Pepper root P&L", signed(pnl.INTARIAN_PEPPER_ROOT ?? 0), "is-pepper"],
      ["Osmium P&L", signed(pnl.ASH_COATED_OSMIUM ?? 0), "is-osmium"],
      ["Largest fall from a peak", fmt(r.max_drawdown), ""],
      ["Fills", nf.format(r.fills), ""],
      ["Units traded", nf.format(r.traded_volume), ""],
      ["Ticks rejected at the position limit", nf.format(r.position_limit_rejections), ""],
    ];
    refs.results.innerHTML = cells.map(([k, v, c]) => `<div class="${c}"><dt>${k}</dt><dd>${v}</dd></div>`).join("");
  }

  function prepareReplay(r) {
    const positions = {};
    for (const g of GOODS) positions[g.key] = new Int16Array(TICKS);
    const running = { pepper: 0, osmium: 0 };
    const marks = r.fill_log.map(([ts, product, qty, price]) => [ts, product === "ASH_COATED_OSMIUM" ? "osmium" : "pepper", qty, price]);
    let f = 0;
    for (let i = 0; i < TICKS; i++) {
      while (f < marks.length && marks[f][0] / 100 <= i) { running[marks[f][1]] += marks[f][2]; f++; }
      positions.pepper[i] = running.pepper;
      positions.osmium[i] = running.osmium;
    }
    return { ...r, marks, equitySeries: r.equity, positions };
  }

  // --- Clock -----------------------------------------------------------------------------
  function tick() {
    const breathing = st.grow >= 1 && !reduced() && st.inView && !document.hidden && !strip();
    if (st.dirty || breathing || pulsePhase() !== null) {
      st.dirty = false;
      draw();
    }
  }
  gsap.ticker.add(tick);
  const ro = new ResizeObserver(resize);
  ro.observe(refs.plot);
  const io = new IntersectionObserver(([entry]) => { st.inView = entry.isIntersecting; });
  io.observe(refs.plot);

  // --- Updates from Python ------------------------------------------------------------------
  function update(component) {
    api.setStateValue = component.setStateValue;
    api.setTriggerValue = component.setTriggerValue;
    const data = component.data || {};
    if (!st.data) {
      if (data.overview) seedOverview(data.overview);
      load(data.static);
    }
    st.data = data;

    if (data.replay_settings) {
      const incoming = data.replay_settings;
      const same = st.settings && ["trader", "day", "match"].every((k) => String(st.settings[k]) === String(incoming[k]));
      if (!st.settings || !st.busy || same) st.settings = { ...incoming };
      renderChoices(data.options);
    }
    if (data.replay) {
      const key = `${data.replay.trader}:${data.replay.day}:${data.replay.match}`;
      if (key !== st.replayKey) {
        st.replayKey = key;
        st.replay = prepareReplay(data.replay);
        st.positions = st.replay.positions;
      }
      const s = st.settings;
      if (s && String(s.trader) === String(data.replay.trader) && String(s.day) === String(data.replay.day) && s.match === data.replay.match) {
        st.busy = false;
        refs.trader.classList.remove("is-busy");
      }
      renderResults();
    }

    const layerChanged = data.layer !== st.layer;
    st.layer = data.layer;
    el.dataset.layer = data.layer;
    for (const a of refs.legend.querySelectorAll("[data-nav]")) {
      if (a.dataset.nav === data.layer) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    }

    if (!st.placed && data.place) {
      st.placed = true;
      const p = data.place;
      if (DAYS.includes(p.day) && Number.isFinite(p.t)) st.probe = DAYS.indexOf(p.day) * TICKS + clamp(Math.round(p.t / 100), 0, TICKS - 1);
      if (data.layer === "ground" && DAYS.includes(p.zoom)) {
        st.zoom = DAYS.indexOf(p.zoom);
        Object.assign(st.win, { a: st.zoom * TICKS, b: (st.zoom + 1) * TICKS });
        st.split = 1;
      }
    }

    if (layerChanged) {
      const toTL = data.layer === "trader" ? 1 : 0;
      if (reduced()) st.tl = toTL; else gsap.to(st, { tl: toTL, duration: 0.7, ease: "power3.inOut", onUpdate: () => { st.dirty = true; } });
      if (data.layer === "trader" && st.settings) zoomTo(DAYS.indexOf(st.settings.day), false);
      else if (data.layer === "notes" || data.layer === "index") zoomTo(null, false);
    }
    renderHead(layerChanged);
    renderCore();
    st.dirty = true;
  }

  function destroy() {
    gsap.ticker.remove(tick);
    ro.disconnect();
    io.disconnect();
    clearTimeout(commitTimer);
  }

  return { update, destroy };
}
