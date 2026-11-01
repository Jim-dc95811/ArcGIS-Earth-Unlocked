# ArcGIS Earth Automation API - working reference

Compiled 2026-11-01 from Esri's documentation and from what Jim's tools already do live. **Documented** = from Esri's pages (which contain small inconsistencies, noted). **Proven** = used successfully by a released tool in Jim's ArcGIS Earth. **Untested** = needs a test on Jim's PC before anything is built on it.

Base URL: `http://localhost:8000` (Settings > Advanced > Automation API). Local calls should bypass any Windows proxy (`urllib.request.build_opener(urllib.request.ProxyHandler({}))`); EarthStick 1.1 and the tracker v1.2 do this. Sources: [Esri overview](https://doc.arcgis.com/en/arcgis-earth/automation-api/overview.htm).

## Endpoints

| Area | Call | Purpose | Status |
|---|---|---|---|
| Camera | `GET /arcgisearth/camera` | current viewpoint (position x/y/z, heading, tilt, roll) | **Proven** (EarthStick, tracker) |
| Camera | `PUT /arcgisearth/camera` | set viewpoint instantly | **Proven** (EarthStick ~10 Hz, tracker recentering) |
| Flight | `POST /arcgisearth/flight` | animated fly-to with a duration | Documented |
| Drawings | `POST /arcgisearth/drawings` | add a point/line/polygon drawing; saved under **My Drawings** | **Proven** (tracker units with picture markers + labels) |
| Drawings | `DELETE /arcgisearth/drawings`, `DELETE /arcgisearth/drawings/{id}` | clear all / delete one | **Proven** (tracker) |
| Graphics | `POST /arcgisearth/graphics`, `GET`/`PATCH`/`DELETE /arcgisearth/graphics/{id}` | temporary graphics; PATCH updates in place | Documented |
| Layers | `POST /arcgisearth/layer` | add a layer by `URI` (or `URIs`) with optional `target` and `type` | Documented |
| Layers | `GET`/`DELETE /arcgisearth/layer/{id}`, `DELETE /arcgisearth/layers/{target}` | load status / remove one / clear a target | Documented |
| Workspace | `GET`/`PUT`/`DELETE /arcgisearth/workspace` | export as .zip / import / clear | Documented |
| Snapshot | `GET /arcgisearth/snapshot` | image of the current view | Documented |

**What the API does NOT have:** no events, no click/selection reporting, no popup control, no way to read which feature the user clicked. Anything that reacts to a click has to go through the object's own popup (KML description links). This is the key constraint for the camera picture-in-picture idea.

## Drawings vs graphics

- **Drawings** appear in the table of contents (My Drawings), accept `title`, `visible` and a `labelSymbol` (`type: text`, `color`, size) for points, and picture markers use `url` + `size`. Esri's text puts the label size in `font.size` but its example puts `size` at the top level; the tracker uses the top-level `size` and it works (**proven**). Response `{"id": ..., "result": "Success"}`. There is no update call: replace = delete + add (the tracker does this). If a user unchecks a drawing, the next add makes it visible again.
- **Graphics** are not documented as appearing in the table of contents, have a PATCH update, and picture markers use `url`, `width`, `height`, `angle`, `xoffset`, `yoffset`. No label field documented. Untested here; a graphic that can be PATCHed may be smoother for moving units than delete+add (worth a test before any tracker change).
- Neither documents attributes or popups. Clickable information still comes from KML/KMZ (Object Factory).
- Esri's own examples are loose about units and formats (`"48px"` vs `48`, RGBA arrays vs hex, `spatialReference.wkid` as string vs number). Send numbers and `{"wkid": 4326}`, and do not expect the response to echo the request exactly.

## Adding layers (`POST /arcgisearth/layer`)

Body `{"URI": "<url or local path>", "target": "operationalLayers" | "baseMaps" | "elevationLayers", "type": "<type>"}`. Types: `ArcGISFeatureService`, `ArcGISMapService`, `ArcGISImageService`, `Shapefile`, `WMS` (type required), `KML` (KML and KMZ), `SceneLayerPackage`, `SceneService`, `RasterDataLayer`, `TilePackage`, `ArcGISMobileScenePackage`, `ArcGISWebScene`, `ArcGISWebMap`, `PortalItem`, `GeoJSON`, `GPX`. Response gives an `id` and `loadStatus`.

Untested but promising: a script could load Object Factory KMZs, Parcel100 GeoJSON cells or a TPKX (`TilePackage` - Esri lists "ArcGIS tile package"; TPKX not named) by path, for example loading the Parcel100 cell under the current camera position. Source: [Add Layer](https://doc.arcgis.com/en/arcgis-earth/automation-api/add-layer.htm).

## Camera body (proven shape)

```json
{"position": {"x": -81.93, "y": 30.39, "z": 1500, "spatialReference": {"wkid": 4326}},
 "heading": 0, "tilt": 60, "roll": 0}
```

EarthStick reads the camera, changes values, and PUTs it back; the tracker changes only x/y so the operator's zoom and tilt are kept.

## Clicks and popups (KML side)

- Object Factory writes an HTML link into the KML description. Any object's popup can also be edited inside ArcGIS Earth: Properties > **Info** tab > **Rich Text / HTML** (raw HTML accepted, no rebuild).
- **Proven 2026-11-01 (Jim's screenshot):** the popup is a built-in web browser. A plain `https://www.fl511.com` link in an object's HTML opened the live, interactive FL511 site **inside the ArcGIS Earth popup**, with back/forward arrows, plus the popup's pin, zoom-to and enlarge buttons. So web-viewable cameras can be shown inside ArcGIS Earth itself, and a pinned popup can act as picture-in-picture. **Also proven (same day):** a live FL511 traffic camera (Tpke MM 3.7 X, 091-003_7X-SB-IPV) played inside the popup after navigating FL511. **Live camera object PROVEN 2026-11-01 (Jim's screenshots):** a KMZ camera object (Object Factory camera icon, 180 m, tether) whose popup HTML holds `<img src="https://fl511.com/map/Cctv/1362">` plus a `<script>` that reloads it every 10 s showed the live SR-200 W of I-95 camera, and the camera's timestamp advanced on its own (10:38:54 -> 10:41:57): **the popup runs JavaScript**. The "OPEN CAMERA PICTURE" link opened the full-size picture inside the popup with a working back arrow. FL511 per-camera picture address: `https://fl511.com/map/Cctv/<id>` (Jim gets it via Edge right-click > **Copy image link**; the `?t=` number is only a cache-buster). Test KMZ: Object Factory branch `camera-pip-test`, `test-builds/TEST_Camera_SR200_W_of_I95.kmz`.
- **Partly tested 2026-11-01:** an `earthpip:test` link with NO handler registered gave "couldn't be opened" (Jim). Inconclusive: an embedded browser normally reports that when Windows has no app for the scheme; only a test with a registered handler shows whether it would launch one. Question: whether a non-web link (a custom scheme such as `earthpip:...`, a `file:` link, or a `localhost` URL) in that panel is handed to Windows. This decides how a click can open a separate always-on-top camera window.

## Ideas this makes possible (none approved)

- **Camera picture-in-picture (Jim, 2026-11-01):** camera object over an intersection. Since the popup is a web browser (above), the simplest route is a link or embedded page inside the popup itself; Jim's original plan is a small Windows always-on-top viewer outside ArcGIS Earth. Trigger options, in order of preference: (1) custom URL scheme registered with Windows; (2) `http://localhost` link served by a small background helper (works with plain web links, but also opens a browser tab). Viewer: refreshing JPEG cameras (many DOT feeds) need only Pillow + Tkinter; true video (HLS) needs VLC/ffmpeg or an embedded browser.
- **Auto-loading layers by location:** watch the camera and `POST /layer` the Parcel100 or Master 4 cell underneath.
- **Scenario / scavenger games:** a script adds drawings or loads clue KMZs as the camera reaches a beacon (camera polling stands in for the missing events).
- **Snapshot capture:** `GET /snapshot` for briefing images or before/after records.
