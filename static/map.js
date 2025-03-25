var map = L.map("map", {
  center: [18.47725505643937, 73.88223574973416],
  crs: L.CRS.EPSG3857,
  ...{
    zoom: 10,
    zoomControl: true,
    preferCanvas: false,
  },
});

var measure_control_f572faae6d3d35d3f9c519c0488effeb = new L.Control.Measure({
  position: "topright",
  primaryLengthUnit: "meters",
  secondaryLengthUnit: "miles",
  primaryAreaUnit: "sqmeters",
  secondaryAreaUnit: "acres",
});
map.addControl(measure_control_f572faae6d3d35d3f9c519c0488effeb);

L.Control.Measure.include({
  _setCaptureMarkerIcon: function () {
    // disable autopan
    this._captureMarker.options.autoPanOnFocus = false;
    // default function
    this._captureMarker.setIcon(
      L.divIcon({
        iconSize: this._map.getSize().multiplyBy(2),
      })
    );
  },
});

var osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  minZoom: 0,
  maxZoom: 18,
  maxNativeZoom: 18,
  noWrap: false,
  attribution: "OpenStreetMap",
  subdomains: "abc",
  detectRetina: false,
  tms: false,
  opacity: 1,
});

// osm.addTo(map);

var satellite = L.tileLayer(
  "https://mt1.google.com/vt/lyrs=s\u0026x={x}\u0026y={y}\u0026z={z}",
  {
    minZoom: 0,
    maxZoom: 18,
    maxNativeZoom: 18,
    noWrap: false,
    attribution: "Google Satellite",
    subdomains: "abc",
    detectRetina: false,
    tms: false,
    opacity: 1,
  }
);

// satellite.addTo(map);

var polygon_51231f7a5495eea78120e43731611725 = L.polygon(
  [
    [18.47725505643937, 73.88223574973416],
    [18.47711749783821, 73.88221884600003],
    [18.477240097517043, 73.88165952518418],
    [18.477057580356615, 73.88162418066938],
    [18.476972349072923, 73.8820045211156],
    [18.476857453365593, 73.8819797237853],
    [18.476793263538152, 73.88254159115249],
    [18.476863129503393, 73.8825542552244],
    [18.476869340404328, 73.88252252655484],
    [18.47705879281195, 73.88256316846389],
    [18.477025990262273, 73.88278551273983],
    [18.47717216637256, 73.88280793926657],
  ],
  {
    bubblingMouseEvents: true,
    color: "red",
    dashArray: null,
    dashOffset: null,
    fill: true,
    fillColor: "cyan",
    fillOpacity: 0.4,
    fillRule: "evenodd",
    lineCap: "round",
    lineJoin: "round",
    noClip: false,
    opacity: 1.0,
    smoothFactor: 1.0,
    stroke: true,
    weight: 3,
  }
).addTo(map);

var popup_f978e3e820c2968e974f31f126358a3a = L.popup({
  maxWidth: "100%",
});

var html_f5182762e8c8f4d99c6d8f6f436fd414 = $(
  `<div id="html_f5182762e8c8f4d99c6d8f6f436fd414" style="width: 100.0%; height: 100.0%;">Polygon Area</div>`
)[0];
popup_f978e3e820c2968e974f31f126358a3a.setContent(
  html_f5182762e8c8f4d99c6d8f6f436fd414
);

polygon_51231f7a5495eea78120e43731611725.bindPopup(
  popup_f978e3e820c2968e974f31f126358a3a
);

var mapAviation_Boundary = L.tileLayer.wms(
  "https://iwmsgis.pmc.gov.in/geoserver/wms?",
  {
    attribution: "",
    format: "image/png",
    layers: "MOD:Aviation_Boundary",
    styles: "",
    transparent: true,
    version: "1.1.1",
  }
);

mapAviation_Boundary.addTo(map);

var Aviation_data = L.tileLayer.wms(
  "https://iwmsgis.pmc.gov.in/geoserver/wms?",
  {
    attribution: "",
    format: "image/png",
    layers: "MOD:Aviation_data",
    opacity: 0.5,
    styles: "",
    transparent: true,
    version: "1.1.1",
  }
);

Aviation_data.addTo(map);

var outward = 1065;
const cqlFilter = `outward ='${outwardNumber}'`;

var boundary = L.tileLayer.wms("https://info.dpzoning.com/geoserver/mod/wms?", {
  attribution: "",
  format: "image/png",
  layers: "mod:points",
  styles: "",
  transparent: true,
  version: "1.1.1",
  CQL_FILTER: cqlFilter
});

//   boundary.setParams({ CQL_FILTER: `outward=${outward}` });
boundary.addTo(map);

var poly_line = L.polyline(
  [
    [18.46982325, 73.79717138],
    [18.477057580356615, 73.88162418066938],
  ],
  {
    bubblingMouseEvents: true,
    color: "yellow",
    dashArray: null,
    dashOffset: null,
    fill: false,
    fillColor: "yellow",
    fillOpacity: 0.2,
    fillRule: "evenodd",
    lineCap: "round",
    lineJoin: "round",
    noClip: false,
    opacity: 1.0,
    smoothFactor: 1.0,
    stroke: true,
    weight: 1,
  }
).addTo(map);

var popup_7480ac6b1c799c9d27aa5fa99d0d83ae = L.popup({
  maxWidth: "100%",
});

map.fitBounds(
  [
    [18.476793263538152, 73.88162418066938],
    [18.47725505643937, 73.88280793926657],
  ],
  {}
);

var layer_control = {
  base_layers: {
    OpenStreetMap: osm,
    "Google Satellite": satellite,
  },
  overlays: {
    "Aviation Boundaries": mapAviation_Boundary,
    "Aviation Zone": Aviation_data,
    "building points": boundary,
  },
};
let layer_control1 = L.control
  .layers(layer_control.base_layers, layer_control.overlays, {
    position: "topright",
    collapsed: true,
    autoZIndex: true,
  })
  .addTo(map);

// cql Fileter code for a polygon and Aviation Boundary layer




// const cqlFilter ="outward ='12345'"
// boundary.setParams({
//   CQL_FILTER: cqlFilter,
//   maxZoom: 19.5,
//   // styles: "Missing_Link_"
// });

// boundary.addTo(map).bringToFront();



// const updateMapWithOutwardNumber = (outwardNumber) => {

//   // Assuming 'boundary' is the existing Leaflet layer for the boundary
//   boundary.setParams({
//     CQL_FILTER: cqlFilter,
//     maxZoom: 19.5,
//   });

//   boundary.addTo(map).bringToFront();
// };