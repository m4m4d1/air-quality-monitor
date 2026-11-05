// Station map and alerts panel. Listens to the dashboard's events from app.js.
(function () {
  "use strict";
  var LABELS = {
    good: ["Good", "Baik"], moderate: ["Moderate", "Sedang"], unhealthy: ["Unhealthy", "Tidak Sehat"],
    very_unhealthy: ["Very unhealthy", "Sangat Tidak Sehat"], hazardous: ["Hazardous", "Berbahaya"]
  };
  var NAMES = { pm25: "PM2.5", pm10: "PM10", o3: "O₃", no2: "NO₂", so2: "SO₂", co: "CO" };
  var map = null;
  var markers = {};

  function esc(s) { var d = document.createElement("div"); d.textContent = s == null ? "" : String(s); return d.innerHTML; }
  function t(en, id) { return '<span class="t-en">' + esc(en) + '</span><span class="t-id">' + esc(id) + "</span>"; }
  function color(category) { return getComputedStyle(document.documentElement).getPropertyValue(category ? "--" + category : "--muted").trim(); }
  function when(ts) { return new Date(ts).toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" }); }

  function drawMap(stations) {
    if (!window.L) return;
    if (!map) {
      map = window.L.map("map", { scrollWheelZoom: false }).setView([-2, 108], 5);
      window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 14, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      }).addTo(map);
      map.fitBounds(stations.map(function (s) { return [s.lat, s.lon]; }), { padding: [24, 24] });
      document.getElementById("legend").innerHTML = Object.keys(LABELS).map(function (k) {
        return '<span class="status s-' + k + '">' + t(LABELS[k][0], LABELS[k][1]) + "</span>";
      }).join("");
    }
    stations.forEach(function (s) {
      var r = s.latest;
      var c = color(r ? r.category : null);
      var popup = "<b>" + esc(s.name) + "</b><br>" + esc(s.city) + " · " + esc(s.province) +
        (r ? "<br>ISPU <b>" + r.index + "</b> · " + t(r.category_label.en, r.category_label.id) +
          "<br>" + t("Dominant: ", "Dominan: ") + esc(NAMES[r.dominant] || "–") : "");
      if (markers[s.id]) {
        markers[s.id].setStyle({ color: c, fillColor: c }).setPopupContent(popup);
      } else {
        markers[s.id] = window.L.circleMarker([s.lat, s.lon], { radius: 9, color: c, fillColor: c, fillOpacity: 0.75, weight: 2 })
          .bindPopup(popup).addTo(map)
          .on("click", function () { document.dispatchEvent(new CustomEvent("aq:select", { detail: s.id })); });
      }
    });
  }

  function drawAlerts(alerts, stations) {
    var names = {};
    stations.forEach(function (s) { names[s.id] = s.name + " (" + s.city + ")"; });
    document.getElementById("alert-count").textContent = alerts.length;
    var list = document.getElementById("alerts");
    if (!alerts.length) {
      list.innerHTML = '<li class="empty">' + t("No station reached Unhealthy in the last 24 hours.",
        "Tidak ada stasiun yang mencapai Tidak Sehat dalam 24 jam terakhir.") + "</li>";
      return;
    }
    list.innerHTML = alerts.slice(0, 60).map(function (a) {
      var span = a.ongoing ? '<span class="live">' + t("ongoing", "berlangsung") + "</span>" : "";
      return '<li data-id="' + esc(a.station_id) + '"><span class="when">' + esc(when(a.start)) + " – " +
        esc(when(a.end)) + " · " + esc(a.hours) + t(" h", " jam") + " " + span + "</span>" +
        "<span><b>" + esc(names[a.station_id] || a.station_id) + '</b> <span class="status s-' + a.category + '">' +
        t(a.category_label.en, a.category_label.id) + "</span></span>" +
        '<span class="what">' + t("Peak ISPU ", "ISPU puncak ") + esc(a.peak_index) + " · " +
        t("dominant ", "dominan ") + esc(NAMES[a.dominant] || a.dominant) + "</span></li>";
    }).join("");
  }

  document.getElementById("alerts").addEventListener("click", function (e) {
    var li = e.target.closest("li[data-id]");
    if (li) document.dispatchEvent(new CustomEvent("aq:select", { detail: li.dataset.id }));
  });

  document.addEventListener("aq:data", async function (e) {
    drawMap(e.detail.stations);
    drawAlerts(await e.detail.api("alerts?hours=24&min_category=unhealthy") || [], e.detail.stations);
  });

  document.addEventListener("aq:selected", function (e) {
    var m = markers[e.detail.id];
    if (m && map) { map.panTo(m.getLatLng()); m.openPopup(); }
  });
})();
