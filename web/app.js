// Air Quality Monitoring System dashboard. Talks to the API; when there is no
// API (the GitHub Pages demo) it reads the same responses from data/demo.json.
(function () {
  "use strict";
  var root = document.documentElement;
  var demo = null;
  var selected = null;
  var chart = null;

  // ---- language ---------------------------------------------------------
  try {
    var saved = localStorage.getItem("lang") || ((navigator.language || "").slice(0, 2) === "id" ? "id" : "en");
    root.dataset.lang = saved;
  } catch (e) {}
  document.querySelector(".lang").addEventListener("click", function () {
    root.dataset.lang = root.dataset.lang === "en" ? "id" : "en";
    try { localStorage.setItem("lang", root.dataset.lang); } catch (e) {}
  });

  function esc(s) { var d = document.createElement("div"); d.textContent = s == null ? "" : String(s); return d.innerHTML; }
  function t(en, id) { return '<span class="t-en">' + esc(en) + '</span><span class="t-id">' + esc(id) + "</span>"; }
  function fmt(v, digits) { return v == null ? "–" : Number(v).toFixed(digits == null ? 1 : digits); }

  // ---- data -------------------------------------------------------------
  async function api(path) {
    if (!demo) {
      try {
        var res = await fetch("api/" + path);
        if (res.ok && (res.headers.get("content-type") || "").indexOf("json") !== -1) return res.json();
      } catch (e) {}
      var file = await fetch("data/demo.json");
      demo = await file.json();
      document.body.classList.add("is-demo");
    }
    return demo.api[path];
  }

  // key, label, unit, digits, averaging period in hours (PermenLHK P.14/2020)
  var POLLUTANTS = [
    ["pm25", "PM2.5", "µg/m³", 1, 24], ["pm10", "PM10", "µg/m³", 1, 24],
    ["o3", "O₃", "µg/m³", 1, 1], ["no2", "NO₂", "µg/m³", 1, 1],
    ["so2", "SO₂", "µg/m³", 1, 24], ["co", "CO", "µg/m³", 0, 8]
  ];
  var NAMES = {};
  POLLUTANTS.forEach(function (p) { NAMES[p[0]] = p[1]; });

  // ---- rendering --------------------------------------------------------
  function statusTag(r) {
    return r ? '<span class="status s-' + r.category + '">' + t(r.category_label.en, r.category_label.id) + "</span>" : "–";
  }

  function renderKpis(summary) {
    var c = summary.category_counts;
    var items = [
      ["var(--accent)", summary.reporting + "/" + summary.stations, "Stations reporting", "Stasiun melapor"],
      ["var(--good)", c.good, "Good", "Baik"],
      ["var(--moderate)", c.moderate, "Moderate", "Sedang"],
      ["var(--unhealthy)", c.unhealthy, "Unhealthy", "Tidak Sehat"],
      ["var(--very_unhealthy)", c.very_unhealthy, "Very unhealthy", "Sangat Tidak Sehat"],
      ["var(--hazardous)", c.hazardous, "Hazardous", "Berbahaya"],
      ["var(--muted)", summary.alerts_24h, "Alerts (24 h)", "Peringatan (24 jam)"]
    ];
    document.getElementById("kpis").innerHTML = items.map(function (k) {
      return '<div class="kpi" style="--c:' + k[0] + '"><b>' + esc(k[1]) + "</b><span>" + t(k[2], k[3]) + "</span></div>";
    }).join("");
  }

  function renderTable(stations) {
    var rows = stations.slice().sort(function (a, b) {
      return (b.latest ? b.latest.index : -1) - (a.latest ? a.latest.index : -1);
    });
    document.getElementById("station-rows").innerHTML = rows.map(function (s) {
      var r = s.latest || {};
      var avg = r.averages || {};
      var over = function (p) { return (r.sub_indices || {})[p] > 100 ? ' class="num bad"' : ' class="num"'; };
      return '<tr data-id="' + esc(s.id) + '"' + (s.id === selected ? ' class="selected"' : "") + ">" +
        "<td><b>" + esc(s.name) + "</b></td><td>" + esc(s.city) + "</td><td>" + statusTag(s.latest) + "</td>" +
        '<td class="num"><b>' + (r.index == null ? "–" : r.index) + "</b></td><td>" + esc(NAMES[r.dominant] || "–") + "</td>" +
        "<td" + over("pm25") + ">" + fmt(avg.pm25) + "</td><td" + over("pm10") + ">" + fmt(avg.pm10) + "</td></tr>";
    }).join("");
  }

  async function renderDetail(station) {
    var r = station.latest;
    document.getElementById("d-name").textContent = station.name;
    document.getElementById("d-where").textContent = station.city + " · " + station.province;
    document.getElementById("d-status").innerHTML = statusTag(r);
    document.getElementById("d-index").textContent = r ? r.index : "–";
    document.getElementById("detail").className = "panel" + (r ? " s-" + r.category : "");
    document.getElementById("d-advice").innerHTML = r ?
      "<b>" + t("Health advice", "Saran kesehatan") + "</b>" + t(r.advice.en, r.advice.id) : "";
    var avg = r ? r.averages : {};
    var subs = r ? r.sub_indices : {};
    document.getElementById("d-params").innerHTML = POLLUTANTS.map(function (p) {
      var cls = "param" + (subs[p[0]] > 100 ? " over" : "") + (r && r.dominant === p[0] ? " dominant" : "");
      return '<div class="' + cls + '"><span>' + esc(p[1]) + " · " + t(p[4] + " h avg", "rerata " + p[4] + " jam") +
        "</span><b>" + fmt(avg[p[0]], p[3]) + "</b> <small>" + p[2] + '</small><span class="sub">ISPU ' +
        (subs[p[0]] == null ? "–" : subs[p[0]]) + "</span></div>";
    }).join("");

    var history = await api("stations/" + station.id + "/readings?hours=72") || [];
    var labels = history.map(function (h) {
      var d = new Date(h.timestamp);
      return d.toLocaleString(root.dataset.lang === "id" ? "id-ID" : "en-GB", { weekday: "short", hour: "2-digit", minute: "2-digit" });
    });
    var style = getComputedStyle(root);
    var datasets = [
      { label: "ISPU", data: history.map(function (h) { return h.index; }), borderColor: style.getPropertyValue("--accent").trim(), yAxisID: "y", borderWidth: 2.5 },
      { label: "PM2.5 (µg/m³)", data: history.map(function (h) { return h.pm25; }), borderColor: style.getPropertyValue("--very_unhealthy").trim(), yAxisID: "y1" },
      { label: "O₃ (µg/m³)", data: history.map(function (h) { return h.o3; }), borderColor: style.getPropertyValue("--moderate").trim(), yAxisID: "y1" },
      { label: "ISPU 100", data: history.map(function () { return 100; }), borderColor: style.getPropertyValue("--unhealthy").trim(), yAxisID: "y", borderDash: [5, 4], borderWidth: 1 }
    ];
    datasets.forEach(function (d) { d.borderWidth = d.borderWidth || 1.5; d.pointRadius = 0; d.tension = 0.3; });
    if (chart) chart.destroy();
    chart = new window.Chart(document.getElementById("d-chart"), {
      type: "line",
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        interaction: { mode: "index", intersect: false },
        plugins: { legend: { labels: { boxWidth: 12, color: style.getPropertyValue("--muted").trim() } } },
        scales: {
          x: { ticks: { maxTicksLimit: 6, color: style.getPropertyValue("--muted").trim() }, grid: { display: false } },
          y: { position: "left", min: 0, title: { display: true, text: "ISPU" }, grid: { color: style.getPropertyValue("--line").trim() } },
          y1: { position: "right", min: 0, title: { display: true, text: "µg/m³ (1 h)" }, grid: { display: false } }
        }
      }
    });
  }

  // ---- wiring -----------------------------------------------------------
  var stationsCache = [];

  function select(id) {
    selected = id;
    var s = stationsCache.find(function (x) { return x.id === id; });
    if (!s) return;
    document.querySelectorAll("#station-rows tr").forEach(function (tr) { tr.classList.toggle("selected", tr.dataset.id === id); });
    renderDetail(s);
    document.dispatchEvent(new CustomEvent("aq:selected", { detail: s }));
  }

  document.getElementById("station-rows").addEventListener("click", function (e) {
    var tr = e.target.closest("tr");
    if (tr) select(tr.dataset.id);
  });
  document.addEventListener("aq:select", function (e) { select(e.detail); });

  async function refresh() {
    var results = await Promise.all([api("stations"), api("summary")]);
    stationsCache = results[0];
    renderKpis(results[1]);
    renderTable(stationsCache);
    var latest = stationsCache.map(function (s) { return s.latest && s.latest.timestamp; }).filter(Boolean).sort().pop();
    document.getElementById("updated").textContent = latest ? new Date(latest).toLocaleString() : "–";
    if (!selected && results[1].worst) selected = results[1].worst.station_id;
    select(selected);
    document.dispatchEvent(new CustomEvent("aq:data", { detail: { stations: stationsCache, api: api } }));
  }

  refresh();
  setInterval(function () { if (!demo) refresh(); }, 60000);
})();
