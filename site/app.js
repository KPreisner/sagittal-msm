// SPDX-License-Identifier: LicenseRef-PolyForm-Strict-1.0.0
// Copyright (c) 2022-2026 Karl Preisner
// Step-through animations for the Sagittal MSM page. Each widget is a function of the step number.
"use strict";

const SVG = "http://www.w3.org/2000/svg";

// The 8 scalars of 8 bits used by the Pippenger and Sagittal examples (most significant bit
// first). They match docs/figures/sagittal.gif and tables.gif.
const MATRIX = ["00110011", "00111000", "10000101", "11111010",
                "00101111", "11101010", "10011001", "10101001"].map((r) => [...r].map(Number));
const ROWS = 8, BITS = 8, G = 4;

// ---------------------------------------------------------------------------------------------
// Helpers

function el(tag, attrs = {}, parent = null, text = null) {
  const node = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text !== null) node.textContent = text;
  if (parent) parent.appendChild(node);
  return node;
}

function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

function txt(parent, x, y, text, attrs = {}) {
  return el("text", { x, y, "font-size": 13, fill: "var(--text)", ...attrs }, parent, text);
}

/** Prev / Play / Next controls for a widget. `render(step)` draws the step and returns the caption
 * (HTML). `count()` returns the number of steps, so widgets can change length. */
function stepper(root, count, render, { interval = 900 } = {}) {
  const controls = root.querySelector("[data-controls]");
  const caption = root.querySelector("[data-caption]");
  const make = (label, cls = "") => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    if (cls) b.className = cls;
    controls.appendChild(b);
    return b;
  };
  const reset = make("Reset"), prev = make("Prev"), play = make("Play", "primary"), next = make("Next");
  const counter = document.createElement("span");
  counter.className = "step-count";
  controls.appendChild(counter);

  let step = 0, timer = null;
  const stop = () => { clearInterval(timer); timer = null; play.textContent = "Play"; };
  const show = () => {
    const n = count();
    step = Math.max(0, Math.min(step, n - 1));
    caption.innerHTML = render(step);
    counter.textContent = `Step ${step + 1} of ${n}`;
    prev.disabled = step === 0;
    next.disabled = step === n - 1;
  };
  reset.onclick = () => { stop(); step = 0; show(); };
  prev.onclick = () => { stop(); step -= 1; show(); };
  next.onclick = () => { stop(); step += 1; show(); };
  play.onclick = () => {
    if (timer) return stop();
    if (step >= count() - 1) step = 0;
    play.textContent = "Pause";
    show();
    timer = setInterval(() => {
      if (step >= count() - 1) return stop();
      step += 1;
      show();
    }, interval);
  };
  show();
  return { refresh: show, restart: () => { stop(); step = 0; show(); } };
}

const sum = (xs) => xs.reduce((a, b) => a + b, 0);
const term = (j) => `P${j}`;

// ---------------------------------------------------------------------------------------------
// 1. A prime-order subgroup: y^2 = x^3 + 3 mod 37 has 39 = 3 * 13 points; G generates 13 of them

function subgroup() {
  const root = document.getElementById("subgroup");
  const svg = root.querySelector("[data-view]");
  const P = 37, B = 3, GEN = [2, 14], W = 640, H = 400, X = 40, Y = 16, S = 9.6;
  const mod = (a) => ((a % P) + P) % P;
  const inv = (a) => { let r = 1; for (let e = P - 2, b = mod(a); e; e >>= 1, b = b * b % P) if (e & 1) r = r * b % P; return r; };
  const add = (p, q) => {
    if (!p) return q;
    if (!q) return p;
    if (p[0] === q[0] && mod(p[1] + q[1]) === 0) return null;
    const lam = p[0] === q[0] ? mod(3 * p[0] * p[0] * inv(2 * p[1])) : mod((q[1] - p[1]) * inv(q[0] - p[0]));
    const x = mod(lam * lam - p[0] - q[0]);
    return [x, mod(lam * (p[0] - x) - p[1])];
  };
  const points = [];
  for (let x = 0; x < P; x++) for (let y = 0; y < P; y++) if (mod(y * y - x ** 3 - B) === 0) points.push([x, y]);
  const multiples = [GEN];
  while (multiples[multiples.length - 1]) multiples.push(add(multiples[multiples.length - 1], GEN));
  const R = multiples.length; // the last entry is null: R·G = O
  const px = ([x]) => X + x * S + S / 2, py = ([, y]) => Y + (P - 1 - y) * S + S / 2;
  const hl = (x) => `<b style="color:var(--sagittal)">${x}</b>`;

  function render(s) {
    clear(svg);
    el("rect", { x: X, y: Y, width: P * S, height: P * S, fill: "none", stroke: "var(--track)" }, svg);
    txt(svg, X, Y + P * S + 16, "x = 0", { "font-size": 11, fill: "var(--text-2)" });
    txt(svg, X + P * S, Y + P * S + 16, `${P - 1}`, { "font-size": 11, fill: "var(--text-2)", "text-anchor": "end" });
    txt(svg, X - 6, Y + P * S, "y = 0", { "font-size": 11, fill: "var(--text-2)", "text-anchor": "end" });
    txt(svg, X - 6, Y + 10, `${P - 1}`, { "font-size": 11, fill: "var(--text-2)", "text-anchor": "end" });
    const shown = multiples.slice(0, Math.min(s, R - 1));
    for (let k = 1; k < shown.length; k++) {
      el("line", { x1: px(shown[k - 1]), y1: py(shown[k - 1]), x2: px(shown[k]), y2: py(shown[k]),
                   stroke: "var(--sagittal)", "stroke-opacity": 0.35, "stroke-width": 1.5 }, svg);
    }
    const inSub = new Set(shown.map((q) => q.join()));
    for (const q of points) {
      const on = inSub.has(q.join());
      el("circle", { cx: px(q), cy: py(q), r: on ? 5 : 3.5, fill: on ? "var(--sagittal)" : "var(--curve)",
                     "fill-opacity": on ? 1 : 0.6 }, svg);
    }
    const lx = X + P * S + 24, ox = lx + 14, oy = 214;
    if (s >= R) {
      const last = multiples[R - 2];
      el("line", { x1: px(last), y1: py(last), x2: ox, y2: oy, stroke: "var(--sagittal)",
                   "stroke-width": 1.5, "stroke-dasharray": "5 4" }, svg);
    }
    if (s > R) {  // O + G = G closes the loop
      el("line", { x1: ox, y1: oy, x2: px(GEN), y2: py(GEN), stroke: "var(--sagittal)",
                   "stroke-width": 1.5, "stroke-dasharray": "5 4" }, svg);
    }
    el("circle", { cx: ox, cy: oy, r: 11, fill: s >= R ? "var(--sagittal)" : "var(--surface)",
                   stroke: s >= R ? "var(--sagittal)" : "var(--curve)", "stroke-width": 2 }, svg);
    txt(svg, ox, oy + 5, "O", { "text-anchor": "middle", "font-size": 14, "font-weight": 700,
                               fill: s >= R ? "#ffffff" : "var(--text)" });
    txt(svg, ox + 20, oy - 3, "O, the identity: not a dot,", { "font-size": 12, fill: "var(--text-2)" });
    txt(svg, ox + 20, oy + 13, "it has no (x, y)", { "font-size": 12, fill: "var(--text-2)" });
    const ring = s >= 1 && s < R ? [shown[shown.length - 1], s === 1 ? "G" : `${s}G`]
               : s > R ? [GEN, `${R + 1}G = G`] : null;
    if (ring) {
      el("circle", { cx: px(ring[0]), cy: py(ring[0]), r: 9, fill: "none", stroke: "var(--sagittal)", "stroke-width": 2 }, svg);
      txt(svg, px(ring[0]) + 11, py(ring[0]) - 8, ring[1], { "font-size": 14, "font-weight": 600 });
    }
    txt(svg, lx, 60, `y² = x³ + ${B}  mod ${P}`, { "font-size": 15 });
    txt(svg, lx, 92, `${points.length} dots + O = ${points.length + 1} points`, { fill: "var(--text-2)" });
    txt(svg, lx, 114, `= ${(points.length + 1) / R} × ${R}`, { fill: "var(--text-2)" });
    if (s >= 1) txt(svg, lx, 150, `reached from G: ${shown.length} dots${s >= R ? " + O" : ""}`, { fill: "var(--sagittal)" });

    if (s === 0) return `The curve y² = x³ + 3 with every number taken mod ${P}: no longer a curve, just ${points.length} dots, plus the identity O. ${points.length + 1} points in all, and ${points.length + 1} = 3 × ${R}.`;
    if (s < R) return `${hl(s === 1 ? "G" : `${s}·G`)}${s === 1 ? ": start at a point G." : ` = ${s - 1}·G + G: add G once more.`} ` +
                      `<span class="sub">Each step hops to another dot (point addition is explained just below).</span>`;
    if (s === R) return `${hl(`${R}·G`)} = ${R - 1}·G + G = ${hl("O")}, the identity: the "zero" of point addition, so P + O = P. ` +
                        `G, 2G, …, ${R - 1}G and O are the subgroup: ${hl(R)} points. ` +
                        `<span class="sub">The other ${points.length - (R - 1)} dots are never reached from G.</span>`;
    return `Keep going: ${hl(`${R + 1}·G`)} = ${R}·G + G = O + G = ${hl("G")}. The loop repeats every ${R} steps, like a clock with ${R} hours, ` +
           `so k·G and (k + ${R})·G are the same point. ` +
           `<span class="sub">Real curves are the same picture at full size, with a clock of about 2<sup>253</sup> hours (next).</span>`;
  }
  stepper(root, () => R + 2, render, { interval: 700 });
}

// ---------------------------------------------------------------------------------------------
// 1. Elliptic-curve addition on y^2 = x^3 + 1 over the reals

function ecAdd() {
  const root = document.getElementById("ecadd");
  const svg = root.querySelector("[data-view]");
  const qSlider = root.querySelector("[data-q]");
  const dbl = root.querySelector("[data-double]");
  const X0 = -1.6, X1 = 2.4, Y = 3.6, W = 640, H = 400;
  const sx = (x) => ((x - X0) / (X1 - X0)) * W;
  const sy = (y) => H / 2 - (y / Y) * (H / 2 - 10);
  const curveY = (x) => Math.sqrt(Math.max(x ** 3 + 1, 0));
  const inView = ([x, y]) => x > X0 && x < X1 && Math.abs(y) < Y;
  const fmt = (v) => v.toFixed(2);

  const branch = (sign) => {
    const pts = [];
    for (let i = 0; i <= 400; i++) {
      const x = -1 + (i / 400) * 3.2;
      pts.push(`${sx(x).toFixed(1)},${sy(sign * curveY(x)).toFixed(1)}`);
    }
    return pts.join(" ");
  };
  const dot = (g, [x, y], label, color, hollow = false, dx = 10, dy = -10) => {
    el("circle", { cx: sx(x), cy: sy(y), r: 6, fill: hollow ? "var(--surface)" : color,
                   stroke: color, "stroke-width": 2.5 }, g);
    if (label) txt(g, sx(x) + dx, sy(y) + dy, label, { "font-size": 15, "font-weight": 600 });
  };

  function render(s) {
    clear(svg);
    const doubling = dbl.checked;
    const q = [Number(qSlider.value), curveY(Number(qSlider.value))];
    const p = doubling ? q : [-0.8, curveY(-0.8)];
    const lam = doubling ? (3 * p[0] ** 2) / (2 * p[1]) : (q[1] - p[1]) / (q[0] - p[0]);
    const x3 = lam ** 2 - p[0] - q[0];
    const r = [x3, lam * (p[0] - x3) - p[1]];
    const third = [x3, -r[1]];

    el("line", { x1: 0, y1: sy(0), x2: W, y2: sy(0), stroke: "var(--track)" }, svg);
    for (const sign of [1, -1]) {
      el("polyline", { points: branch(sign), fill: "none", stroke: "var(--curve)", "stroke-width": 2 }, svg);
    }
    if (s >= 3) {
      const xs = [Math.min(p[0], q[0], third[0]) - 0.5, Math.max(p[0], q[0], third[0]) + 0.5];
      el("line", { x1: sx(xs[0]), y1: sy(p[1] + lam * (xs[0] - p[0])), x2: sx(xs[1]),
                   y2: sy(p[1] + lam * (xs[1] - p[0])), stroke: "var(--sagittal)", "stroke-width": 2.5 }, svg);
    }
    if (s >= 5) {
      el("line", { x1: sx(third[0]), y1: sy(third[1]), x2: sx(r[0]), y2: sy(r[1]),
                   stroke: "var(--text-2)", "stroke-width": 1.6, "stroke-dasharray": "5 4" }, svg);
    }
    if (s >= 4 && inView(third)) dot(svg, third, "", "var(--text-2)", true);
    if (s >= 1) dot(svg, p, "P", "var(--text)", false, -22, -10);
    if (s >= 2 && !doubling) dot(svg, q, "Q", "var(--text)", false, 10, 18);
    if (s >= 6 && inView(r)) dot(svg, r, doubling ? "2P" : "P + Q", "var(--result)", false, 10, 22);

    const off = !inView(third) || !inView(r) ? " (Part of this falls outside the drawing; move Q.)" : "";
    const captions = [
      "The curve y² = x³ + 1, drawn over the real numbers.",
      "Take a point P on the curve.",
      doubling ? "To double P, there is no second point: use P twice." : "Take a second point Q.",
      doubling ? "Draw the tangent line at P." : "Draw the line through P and Q.",
      "The line meets the curve at exactly one more point." + off,
      "Reflect that point across the x-axis.",
      `That point is ${doubling ? "2P" : "P + Q"} = (${fmt(r[0])}, ${fmt(r[1])}), with slope λ = ${fmt(lam)}.` + off,
    ];
    return captions[s];
  }
  const s = stepper(root, () => 7, render, { interval: 1100 });
  qSlider.oninput = s.refresh;
  dbl.onchange = s.refresh;
}

// ---------------------------------------------------------------------------------------------
// 1. Double-and-add

function doubleAndAdd() {
  const pts = (m) => (m === 1 ? "P" : `${m}P`); // the running value, as a multiple of P
  const root = document.getElementById("dbladd");
  const table = root.querySelector("[data-view]");
  const input = root.querySelector("[data-k]");
  const k = () => Math.max(1, Math.min(1e9, Math.floor(Number(input.value) || 1)));
  const bits = () => k().toString(2);

  function render(s) {
    const b = bits();
    let value = 1, doubles = 0, adds = 0, lastOp = "";
    const rows = [`<tr><th>bit</th><th>step</th><th>value</th></tr>`,
                  `<tr><td>${b[0]}</td><td>start with P</td><td>P</td></tr>`];
    for (let i = 1; i <= s; i++) {
      const prev = value;
      value *= 2; doubles++;
      let op = `double ${pts(prev)} → ${pts(value)}`;
      if (b[i] === "1") { value += 1; adds++; op += `, add P → ${pts(value)}`; }
      if (i === s) lastOp = op;
      const last = i === s;
      rows.push(`<tr${last ? ' style="background:color-mix(in srgb, var(--sagittal) 18%, transparent)"' : ""}>` +
                `<td>${b[i]}</td><td>${op}</td><td>${pts(value)}</td></tr>`);
    }
    table.innerHTML = rows.join("");
    // Describe the row just added, with its bit highlighted in k's binary form.
    const marked = [...b].map((bit, i) => (i === s ? `<b style="color:var(--sagittal)">${bit}</b>` : bit)).join("");
    const binary = `k = ${k()} = <span class="mono">${marked}</span> in binary.`;
    let what;
    if (s === 0) what = `Bit 1 of ${b.length} is the leading 1: start with P.`;
    else what = `Bit ${s + 1} of ${b.length} is ${b[s]}: ${lastOp}.`;
    if (s < b.length - 1) return `${binary} ${what}`;
    return `${binary} ${what} <b>${k()}·P took ${doubles} doublings + ${adds} additions = ` +
           `${doubles + adds} operations</b>, instead of ${(k() - 1).toLocaleString()} additions one P at a time.`;
  }
  const s = stepper(root, () => bits().length, render, { interval: 800 });
  input.oninput = s.restart;
}

// ---------------------------------------------------------------------------------------------
// 2. A 377-bit multiplication as 32-bit word products

function limbs() {
  const root = document.getElementById("limbs");
  const svg = root.querySelector("[data-view]");
  const N = 12, C = 19, X = 70;
  function render(s) {
    clear(svg);
    for (const [name, y] of [["a", 10], ["b", 36]]) {
      txt(svg, X - 14, y + 15, name, { "text-anchor": "end", "font-size": 15 });
      for (let i = 0; i < N; i++) {
        el("rect", { x: X + i * C, y, width: C - 3, height: C - 3, rx: 3, fill: "var(--sagittal)",
                     "fill-opacity": 0.3, stroke: "var(--sagittal)" }, svg);
      }
    }
    txt(svg, X + N * C + 12, 23, "12 words of 32 bits each", { fill: "var(--text-2)" });
    txt(svg, X - 14, 80 + (N * C) / 2, "a × b", { "text-anchor": "end", "font-size": 15 });
    const rowsDone = Math.min(s, N);
    for (let i = 0; i < N; i++) {
      for (let j = 0; j < N; j++) {
        const done = i < rowsDone;
        el("rect", { x: X + j * C, y: 72 + i * C, width: C - 3, height: C - 3, rx: 3,
                     fill: done ? "var(--pippenger)" : "none", "fill-opacity": 0.35,
                     stroke: done ? "var(--pippenger)" : "var(--track)" }, svg);
      }
    }
    const lines = [
      [`${rowsDone * N} of 144 word multiplications`, "var(--text)"],
      [s > N ? "+ about 156 to reduce the result mod p" : "", "var(--text)"],
      [s > N ? "≈ 300 multiply-adds per field multiplication" : "", "var(--text-2)"],
      [s > N + 1 ? "× 10 per mixed add ≈ 3,000 per curve addition" : "", "var(--text-2)"],
    ];
    lines.forEach(([t, fill], i) => txt(svg, X + N * C + 24, 110 + i * 30, t, { fill, "font-size": 14 }));
    const a = `<b style="color:var(--sagittal)">a</b>`, b = `<b style="color:var(--sagittal)">b</b>`;
    if (s === 0) return `Each orange cell will be one 32 × 32 → 64-bit multiplication of a word of ${a} by a word of ${b}.`;
    if (s <= N) return `Row ${s}: word ${s} of ${a} times all 12 words of ${b}, with carries passed along.`;
    if (s === N + 1) return "Then the 24-word product is reduced mod p (Montgomery): about 300 multiply-adds in all.";
    return "A mixed curve addition needs 10 field multiplications: about 3,000 word multiply-adds.";
  }
  stepper(root, () => N + 3, render, { interval: 500 });
}

// ---------------------------------------------------------------------------------------------
// 2. Thread contention: one warp updating buckets

function contention() {
  const root = document.getElementById("contention");
  const svg = root.querySelector("[data-view]");
  const caption = root.querySelector("[data-caption]");
  const T = 32, B = 15, W = 640;
  function draw() {
    clear(svg);
    const digits = Array.from({ length: T }, () => Math.floor(Math.random() * 16));
    const loads = Array(B + 1).fill(0);
    digits.forEach((d) => { if (d) loads[d]++; });
    const busiest = Math.max(...loads);
    const colliding = sum(loads.filter((n) => n > 1));
    const tx = (i) => 16 + i * ((W - 32) / (T - 1));
    const bx = (d) => 30 + (d - 1) * ((W - 60) / (B - 1));

    const panel = (y0, title, targets, count, bucketLabel) => {
      txt(svg, 8, y0, title, { "font-size": 14, "font-weight": 600 });
      for (let i = 0; i < T; i++) {
        const t = targets(i);
        if (t !== null) {
          el("line", { x1: tx(i), y1: y0 + 18, x2: t.x, y2: y0 + 96, stroke: t.color,
                       "stroke-opacity": 0.75, "stroke-width": 1.4 }, svg);
        }
        el("rect", { x: tx(i) - 5, y: y0 + 10, width: 10, height: 10, rx: 2,
                     fill: t === null ? "var(--track)" : "var(--text-2)" }, svg);
      }
      for (const [x, n, color] of count) {
        el("rect", { x: x - 9, y: y0 + 96, width: 18, height: 18, rx: 3, fill: color,
                     "fill-opacity": n > 1 ? 0.9 : 0.35, stroke: color }, svg);
        if (n > 1) txt(svg, x, y0 + 109, String(n), { "text-anchor": "middle", "font-size": 11,
                                                      fill: "#ffffff", "font-weight": 700 });
      }
      txt(svg, W - 8, y0, bucketLabel, { "text-anchor": "end", fill: "var(--text-2)" });
    };
    panel(16, "Pippenger: 32 threads, one point each, bucket = the point's 4-bit digit",
          (i) => (digits[i] ? { x: bx(digits[i]), color: loads[digits[i]] > 1 ? "var(--pippenger)" : "var(--curve)" } : null),
          Array.from({ length: B }, (_, j) => [bx(j + 1), loads[j + 1], "var(--pippenger)"]),
          "");
    panel(160, "Sagittal: 32 threads, one per scalar bit, each owns its bucket",
          (i) => ({ x: tx(i), color: "var(--sagittal)" }),
          Array.from({ length: T }, (_, i) => [tx(i), 1, "var(--sagittal)"]),
          "");
    const hl = (x) => `<b style="color:var(--pippenger)">${x}</b>`;
    caption.innerHTML =
      `Pippenger: ${hl(colliding)} of 32 threads hit a bucket another thread is also updating. The ` +
      `busiest bucket gets ${hl(busiest)} updates, which must happen one after another (or the points ` +
      `must be sorted by bucket first). Grey threads drew digit 0 and sit idle. ` +
      `<span class="sub">Sagittal: 32 threads, 32 buckets, no collisions, every thread busy.</span>`;
  }
  root.querySelector("[data-shuffle]").onclick = draw;
  draw();
}

// ---------------------------------------------------------------------------------------------
// Bit-matrix drawing shared by the Pippenger and Sagittal widgets

const CELL = 26, MX = 52, MY = 34;

function drawMatrix(svg, highlight) {
  for (let col = 0; col < BITS; col++) {
    txt(svg, MX + col * CELL + CELL / 2, MY - 10, String(BITS - 1 - col),
        { "text-anchor": "middle", "font-size": 11, fill: "var(--text-2)" });
  }
  txt(svg, MX - 8, MY - 10, "bit", { "text-anchor": "end", "font-size": 11, fill: "var(--text-2)" });
  for (let r = 0; r < ROWS; r++) {
    txt(svg, MX - 8, MY + r * CELL + 17, `k${r + 1}`, { "text-anchor": "end", fill: "var(--text-2)" });
    for (let col = 0; col < BITS; col++) {
      el("rect", { x: MX + col * CELL, y: MY + r * CELL, width: CELL, height: CELL,
                   fill: "var(--surface)", stroke: "var(--track)" }, svg);
      txt(svg, MX + col * CELL + CELL / 2, MY + r * CELL + 17, String(MATRIX[r][col]),
          { "text-anchor": "middle", "font-size": 14 });
    }
  }
  if (highlight) {
    const [col, row, w, h, color] = highlight;
    el("rect", { x: MX + col * CELL + 2, y: MY + row * CELL + 2, width: w * CELL - 4,
                 height: h * CELL - 4, rx: 5, fill: color, "fill-opacity": 0.28, stroke: color,
                 "stroke-width": 2.5 }, svg);
  }
}

// ---------------------------------------------------------------------------------------------
// 3. Pippenger's bucket method: c = 4, two windows

function pippenger() {
  const root = document.getElementById("pip");
  const svg = root.querySelector("[data-view]");
  const C = 4, WINDOWS = BITS / C, BUCKETS = (1 << C) - 1;
  const digit = (r, w) => parseInt(MATRIX[r].slice(w * C, w * C + C).join(""), 2); // w = 0 is the high window
  const placeSteps = ROWS * WINDOWS;
  const total = 1 + placeSteps + WINDOWS + 1;

  function bucketsFor(w, upTo) {
    const buckets = Array.from({ length: BUCKETS + 1 }, () => []);
    for (let r = 0; r < upTo; r++) { const d = digit(r, w); if (d) buckets[d].push(r + 1); }
    return buckets;
  }
  function reduceCost(buckets) {
    const touched = buckets.map((b, d) => (d && b.length ? d : 0)).filter(Boolean);
    return touched.length ? touched.length - 1 + (Math.max(...touched) - 1) : 0;
  }

  function render(s) {
    clear(svg);
    let w = 0, upTo = 0, row = null;
    if (s >= 1 && s <= placeSteps) { w = Math.floor((s - 1) / ROWS); upTo = ((s - 1) % ROWS) + 1; row = upTo - 1; }
    else if (s > placeSteps) { w = Math.min(s - placeSteps - 1, WINDOWS - 1); upTo = ROWS; }
    drawMatrix(svg, s === 0 ? null : row === null ? [w * C, 0, C, ROWS, "var(--pippenger)"]
                                                    : [w * C, row, C, 1, "var(--pippenger)"]);
    if (s > 0) {
      el("rect", { x: MX + w * C * CELL + 1, y: MY + 1, width: C * CELL - 2, height: ROWS * CELL - 2,
                   rx: 5, fill: "none", stroke: "var(--pippenger)", "stroke-width": 1.2 }, svg);
    }
    const buckets = bucketsFor(w, upTo);
    const bx = 330, top = 24;
    txt(svg, bx, top - 6, `window ${w === 0 ? "bits 7–4" : "bits 3–0"}: buckets`, { fill: "var(--text-2)", "font-size": 12 });
    for (let d = 1; d <= BUCKETS; d++) {
      const y = top + d * 18;
      const active = row !== null && digit(row, w) === d;
      if (active) el("rect", { x: bx - 4, y: y - 13, width: 300, height: 17, rx: 3,
                               fill: "var(--pippenger)", "fill-opacity": 0.18 }, svg);
      txt(svg, bx, y, `${d.toString(2).padStart(4, "0")}  (${d})`, { "font-size": 12, fill: "var(--text-2)", class: "mono" });
      txt(svg, bx + 92, y, buckets[d].map(term).join(" + "), { "font-size": 12 });
    }
    const adds = sum(buckets.map((b) => Math.max(0, b.length - 1)));
    if (s === 0) return "8 scalars of 8 bits. With c = 4 there are two windows (bits 7–4 and 3–0) and 15 buckets per window.";
    const hl = (x) => `<b style="color:var(--pippenger)">${x}</b>`;
    if (row !== null) {
      const d = digit(row, w), k = hl(`k${row + 1}`);
      return d ? `${k}'s digit in this window is ${d.toString(2).padStart(4, "0")} = ${hl(d)}: P${row + 1} goes into bucket ${hl(d)}. ` +
                 `<span class="sub">Additions so far in this window: ${hl(adds)}.</span>`
               : `${k}'s digit in this window is ${hl(0)}: P${row + 1} is skipped.`;
    }
    if (s <= placeSteps + WINDOWS) {
      return `Reduce this window: Σ d·bucket[d] with two running sums from the top bucket down, ` +
             `${hl(reduceCost(buckets))} more additions. This can only start once every bucket is final.`;
    }
    return "Combine the windows: result = 2⁴·(high window) + (low window): 4 doublings and 1 addition. " +
           "<span class=\"sub\">At real sizes, buckets number in the hundreds of thousands.</span>";
  }
  stepper(root, () => total, render, { interval: 700 });
}

// ---------------------------------------------------------------------------------------------
// 4. Sagittal: tables (once per proving key), then accumulation (every proof)

const SIZE = (1 << G) - 1;
const members = (mask, batch) => [...Array(G).keys()].filter((t) => (mask >> t) & 1).map((t) => batch * G + t + 1);
const entry = (mask, batch) => members(mask, batch).map(term).join(" + ");
const patternOf = (mask) => [...Array(G).keys()].map((t) => (mask >> t) & 1).join("");
const SOURCES = [...Array(SIZE).keys()].map((c) => { const d = c & (c + 1); return d ? [c - d, d - 1] : null; });

function tables() {
  const root = document.getElementById("tables");
  const table = root.querySelector("[data-view]");
  function render(s) {
    const building = s < SIZE ? s : null;
    const sources = building === null ? [] : SOURCES[building] || [];
    let additions = 0;
    const rows = [`<tr><th>bits</th><th>batch 1 table (P1..P4)</th><th>batch 2 table (P5..P8)</th><th>built as</th></tr>`];
    for (let c = 0; c < SIZE; c++) {
      const done = c <= s, mask = c + 1;
      let bg = "";
      if (c === building) bg = "color-mix(in srgb, var(--sagittal) 25%, transparent)";
      else if (sources.includes(c)) bg = "color-mix(in srgb, var(--result) 20%, transparent)";
      let how = "";
      if (done) {
        if (SOURCES[c]) { additions++; how = `(${entry(SOURCES[c][0] + 1, 0)}) + (${entry(SOURCES[c][1] + 1, 0)})`; }
        else how = "input point, no addition";
      }
      rows.push(`<tr style="${bg ? `background:${bg};` : ""}${done ? "" : "color:var(--muted)"}">` +
                `<td class="mono">${patternOf(mask)}</td><td>${done ? entry(mask, 0) : ""}</td>` +
                `<td>${done ? entry(mask, 1) : ""}</td><td style="color:var(--text-2)">${how}</td></tr>`);
    }
    table.innerHTML = rows.join("");
    if (building !== null) {
      return `Entry ${building + 1} of ${SIZE}: ${SOURCES[building] ? "adds the two highlighted entries built earlier" : "a single input point, no addition"}. ` +
             `<span class="sub">Additions so far: ${additions} per batch.</span>`;
    }
    return `All ${SIZE} combinations of each batch's 4 points, built with ${SIZE - G} additions per batch. ` +
           `<span class="sub">n points in batches of g need n/g tables of 2<sup>g</sup> − 1 entries.</span>`;
  }
  stepper(root, () => SIZE + 1, render, { interval: 700 });
}

function accumulate() {
  const root = document.getElementById("accumulate");
  const svg = root.querySelector("[data-view]");
  const steps = [];
  for (let batch = 0; batch < ROWS / G; batch++) for (let col = 0; col < BITS; col++) steps.push([batch, col]);
  const subset = (batch, col) => [...Array(G).keys()].filter((t) => MATRIX[batch * G + t][col]).map((t) => batch * G + t + 1);

  function render(s) {
    clear(svg);
    const current = s < steps.length ? steps[s] : null;
    const combining = s > steps.length ? s - steps.length - 1 : null; // bucket rows combined so far
    drawMatrix(svg, current ? [current[1], current[0] * G, 1, G, "var(--sagittal)"] : null);
    el("line", { x1: MX, y1: MY + G * CELL, x2: MX + BITS * CELL, y2: MY + G * CELL,
                 stroke: "var(--text-2)", "stroke-width": 1.5 }, svg);
    txt(svg, MX + BITS * CELL + 6, MY + 2 * CELL, "batch 1", { "font-size": 11, fill: "var(--text-2)" });
    txt(svg, MX + BITS * CELL + 6, MY + 6 * CELL, "batch 2", { "font-size": 11, fill: "var(--text-2)" });

    const done = steps.slice(0, current ? s + 1 : steps.length);
    const bx = 330;
    txt(svg, bx, MY - 10, "bucket", { "font-size": 11, fill: "var(--text-2)" });
    let additions = 0, bucketAdditions = 0;
    for (let col = 0; col < BITS; col++) {
      const y = MY + col * CELL + 17;
      const terms = done.filter(([b, c]) => c === col && subset(b, c).length).map(([b, c]) => `(${subset(b, c).map(term).join("+")})`);
      additions += Math.max(0, terms.length - 1);
      if (current && current[1] === col) bucketAdditions = Math.max(0, terms.length - 1);
      if ((current && current[1] === col) || (combining !== null && col <= combining))
        el("rect", { x: bx - 4, y: y - 15, width: 300, height: 21, rx: 3, fill: "var(--sagittal)",
                     "fill-opacity": combining !== null && col < combining ? 0.06 : 0.14 }, svg);
      txt(svg, bx, y, `bit ${BITS - 1 - col}`, { fill: "var(--text-2)", "font-size": 12 });
      txt(svg, bx + 46, y, terms.join(" + "), { "font-size": 12 });
    }
    if (current) {
      const [batch, col] = current;
      const bits = [...Array(G).keys()].map((t) => MATRIX[batch * G + t][col]).join("");
      const chosen = subset(batch, col).map(term).join(" + ");
      const hl = (x) => `<b style="color:var(--sagittal)">${x}</b>`, bit = hl(BITS - 1 - col);
      return `Batch ${hl(batch + 1)}, bit ${bit}: bits <span class="mono">${bits}</span> → ` +
             (chosen ? `table entry ${chosen} → bucket for bit ${bit}.` : "all zeros, nothing to add.") +
             ` <span class="sub">Additions into bit ${bit}'s bucket so far: ${hl(bucketAdditions)}.</span>`;
    }
    if (combining === null) {
      return `Every block done: 8 buckets, one per bit, ${additions} additions. Next, combine them from the top: ` +
             `result = 2·result + bucket, once per bit.`;
    }
    const hl = (x) => `<b style="color:var(--sagittal)">${x}</b>`;
    // Build the expression up to the previous bit, then add this step's 2 and bucket highlighted.
    const step = (inner, k, two = "2", b = `b${BITS - 1 - k}`) => `${k === 1 ? `${two}·${inner}` : `${two}(${inner})`} + ${b}`;
    let expr = `b${BITS - 1}`;
    for (let k = 1; k < combining; k++) expr = step(expr, k);
    expr = combining === 0 ? hl(expr) : step(expr, combining, hl("2"), hl(`b${BITS - 1 - combining}`));
    const tail = combining === BITS - 1
      ? ` <span class="sub">Done: ${BITS - 1} doublings for all n points. No bucket reduction, and each bucket's work was fixed in advance.</span>`
      : "";
    return `Combine, bit ${hl(BITS - 1 - combining)}: result = ${expr}. ` +
           `<span class="sub">Doublings so far: ${hl(combining)}.</span>` + tail;
  }
  stepper(root, () => steps.length + 1 + BITS, render, { interval: 750 });
}

// ---------------------------------------------------------------------------------------------

subgroup();
ecAdd();
doubleAndAdd();
limbs();
contention();
pippenger();
tables();
accumulate();
