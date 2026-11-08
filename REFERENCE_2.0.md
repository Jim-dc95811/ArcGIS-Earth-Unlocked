# ArcGIS Earth Unlocked - 2.0 Reference (8 November 2026)

> 🤖 **Using AI assistance?** Have the agent read the [CLAUDE.md](CLAUDE.md) file first.

On 8 November 2026 Jim Gaddy moved every tool in the family to **2.0** at once, so that this day's working set is one known-good reference point. Every tool below was run by Jim on Windows with ArcGIS Earth before it was published. The table **Reference commits** below names the exact commit of each repository that holds this state - later commits may follow, and that commit stays the reference.

**What changed for 2.0:** EarthStick 2.0 and World Gate Maker 2.0 bring new features (gates picked up while you fly, the + ADD GATES button, dropped gates that face each other - see the [EarthStick 2.0 change document](https://github.com/Jim-dc95811/EarthStick/blob/main/docs/EARTHSTICK_V2.0_CHANGES.md)). Every other tool is the same program as before with only its version text changed (checked line by line). The PRAVE / RMC Field Decoder Tester stays *Version 1.0 Gold* - Jim's own program, published unchanged. Older zips are kept in each repository's `archive/` folder. The download links on this page are pinned to the reference commits, so they keep giving exactly the 2.0 files after later releases (for example Object Factory 2.1).

**How to check a copy:** on Windows, open PowerShell in the folder with the zip and type `Get-FileHash <zip name>` - the SHA-256 must match the zip line below. For a file you already extracted, `Get-FileHash "System Files\<file>"` must match its line.

| Tool | Download | Folder inside |
|---|---|---|
| MBTiles to TPKX converter (mb2tpkx) | [mb2tpkx.zip](https://github.com/Jim-dc95811/QGIS-Mbtile-to-ArcGIS-Earth-TPKX/raw/f923f62eff78a639f19872db711fb472775330df/mb2tpkx.zip) | `mb2tpkx_v2.0` |
| Master 4 Grid Maker | [Master4_Grid_Maker.zip](https://github.com/Jim-dc95811/QGIS-Mbtile-to-ArcGIS-Earth-TPKX/raw/f923f62eff78a639f19872db711fb472775330df/Master4_Grid_Maker.zip) | `Master4_Grid_Maker_v2.0` |
| PRAVE ME Tracker | [PRAVE_ME_Tracker_v1.zip](https://github.com/Jim-dc95811/ArcGIS-Earth-Offline-Maps-Chartplotting/raw/c2b329a11863ef2cf20759685ab1be0aac27d6f8/downloads/PRAVE_ME_Tracker_v1.zip) | `PRAVE_ME_Tracker_v2.0` |
| PRAVE RMC Field Decoder Tester Gold | [PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold.zip](https://github.com/Jim-dc95811/ArcGIS-Earth-Offline-Maps-Chartplotting/raw/c2b329a11863ef2cf20759685ab1be0aac27d6f8/downloads/PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold.zip) | `PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold` |
| TPKX Batch Factory | [TPKX_Batch_Factory_v1.zip](https://github.com/Jim-dc95811/ArcGIS-Earth-Offline-Maps-Chartplotting/raw/c2b329a11863ef2cf20759685ab1be0aac27d6f8/downloads/TPKX_Batch_Factory_v1.zip) | `TPKX_Batch_Factory_v2.0` |
| EarthStick | [EarthStick_v2.0.zip](https://github.com/Jim-dc95811/EarthStick/raw/d54e3a132f1e2699e627f027562def0a789b196b/releases/EarthStick_v2.0.zip) | `EarthStick_v2.0` |
| World Gate Maker | [World_Gate_Maker_v2.0.zip](https://github.com/Jim-dc95811/EarthStick/raw/d54e3a132f1e2699e627f027562def0a789b196b/releases/World_Gate_Maker_v2.0.zip) | `World_Gate_Maker_v2.0` |
| Object Factory | [ArcGIS_Earth_Object_Factory_v2.0.zip](https://github.com/Jim-dc95811/ArcGIS-Earth-Object-Factory/raw/2b86893f368c0ed4babbc59acc3c216a327fc9b3/releases/ArcGIS_Earth_Object_Factory_v2.0.zip) | `Object_Factory_v2.0` |
| PointLayer | [PointLayer_v2.0.zip](https://github.com/Jim-dc95811/Point-Maps/raw/80a9c0a5d3eaebdbd9bf57209888a71e26074a69/releases/PointLayer_v2.0.zip) | `PointLayer_v2.0` |
| Parcel100 | [Parcel100_v2.0.zip](https://github.com/Jim-dc95811/Parcel100/raw/2428eef41fa36018ec7a5a8289eed254d05ed50c/downloads/Parcel100_v2.0.zip) | `Parcel100_v2.0` |
| Picture World Maker | [Picture_World_Maker_v2.0.zip](https://github.com/Jim-dc95811/Picture-World-Maker/raw/b164827bc8b77c7464977d7ef0e7c4a9b7ab802d/releases/Picture_World_Maker_v2.0.zip) | `Picture_World_Maker_v2.0` |

## Reference commits

| Repository | Commit |
|---|---|
| [ArcGIS-Earth-Object-Factory](https://github.com/Jim-dc95811/ArcGIS-Earth-Object-Factory) | [`2b86893`](https://github.com/Jim-dc95811/ArcGIS-Earth-Object-Factory/tree/2b86893f368c0ed4babbc59acc3c216a327fc9b3) |
| [ArcGIS-Earth-Offline-Maps-Chartplotting](https://github.com/Jim-dc95811/ArcGIS-Earth-Offline-Maps-Chartplotting) | [`c2b329a`](https://github.com/Jim-dc95811/ArcGIS-Earth-Offline-Maps-Chartplotting/tree/c2b329a11863ef2cf20759685ab1be0aac27d6f8) |
| [ArcGIS-Earth-Unlocked](https://github.com/Jim-dc95811/ArcGIS-Earth-Unlocked) | [`f76c044`](https://github.com/Jim-dc95811/ArcGIS-Earth-Unlocked/tree/f76c04468731ae1f5bdf7491a2d59253de8a962c) |
| [EarthStick](https://github.com/Jim-dc95811/EarthStick) | [`d54e3a1`](https://github.com/Jim-dc95811/EarthStick/tree/d54e3a132f1e2699e627f027562def0a789b196b) |
| [Parcel100](https://github.com/Jim-dc95811/Parcel100) | [`2428eef`](https://github.com/Jim-dc95811/Parcel100/tree/2428eef41fa36018ec7a5a8289eed254d05ed50c) |
| [Picture-World-Maker](https://github.com/Jim-dc95811/Picture-World-Maker) | [`b164827`](https://github.com/Jim-dc95811/Picture-World-Maker/tree/b164827bc8b77c7464977d7ef0e7c4a9b7ab802d) |
| [Point-Maps](https://github.com/Jim-dc95811/Point-Maps) | [`80a9c0a`](https://github.com/Jim-dc95811/Point-Maps/tree/80a9c0a5d3eaebdbd9bf57209888a71e26074a69) |
| [QGIS-Mbtile-to-ArcGIS-Earth-TPKX](https://github.com/Jim-dc95811/QGIS-Mbtile-to-ArcGIS-Earth-TPKX) | [`f923f62`](https://github.com/Jim-dc95811/QGIS-Mbtile-to-ArcGIS-Earth-TPKX/tree/f923f62eff78a639f19872db711fb472775330df) |

## MBTiles to TPKX converter (mb2tpkx)

Zip [`mb2tpkx.zip`](https://github.com/Jim-dc95811/QGIS-Mbtile-to-ArcGIS-Earth-TPKX/raw/f923f62eff78a639f19872db711fb472775330df/mb2tpkx.zip) (repository [QGIS-Mbtile-to-ArcGIS-Earth-TPKX](https://github.com/Jim-dc95811/QGIS-Mbtile-to-ArcGIS-Earth-TPKX)):

`4e66e612b00b751aafa4fb8b0169c78946866840ce0395a0097661b177d33c1e`

| File | SHA-256 |
|---|---|
| `mb2tpkx_v2.0/System Files/Ready_To_Fly.ps1` | `58ab0bb86261c1d1c3820cd20353d6ca68b86e2bc0983eae09a7cbc4bdc90749` |
| `mb2tpkx_v2.0/System Files/mb2tpkx.py` | `d38157740e67164213e742c22dd37fc3896bc9a06d84ced335179ea12025a8c2` |
| `mb2tpkx_v2.0/mb2tpkx.bat` | `231de368fedef31bea2dbe1c0da584f2338c1e135e9669aa83e7925beadd85e1` |
| `mb2tpkx_v2.0/mb2tpkx_User_Manual.pdf` | `3bbc5f542024d28cd8bb0b8c9778cebafef80cb7df93d575ef2199aec72f1d66` |

## Master 4 Grid Maker

Zip [`Master4_Grid_Maker.zip`](https://github.com/Jim-dc95811/QGIS-Mbtile-to-ArcGIS-Earth-TPKX/raw/f923f62eff78a639f19872db711fb472775330df/Master4_Grid_Maker.zip) (repository [QGIS-Mbtile-to-ArcGIS-Earth-TPKX](https://github.com/Jim-dc95811/QGIS-Mbtile-to-ArcGIS-Earth-TPKX)):

`1ed0d60d02263a95600d42e64c9419f483b2b00bddf9b3435a80481adfc4d590`

| File | SHA-256 |
|---|---|
| `Master4_Grid_Maker_v2.0/Master4_Grid_Maker.bat` | `c0d772fe21cbd6a85e7eb9021b15102556005b702b573370b163a38b5540e736` |
| `Master4_Grid_Maker_v2.0/Master4_Grid_Maker_User_Manual.pdf` | `8c6fe5a598a7bd2c091b594e3976b0a02aa08791309501b6b2da280bdc6358de` |
| `Master4_Grid_Maker_v2.0/System Files/Master4_Grid_Maker.py` | `1c131b86144e98cf2aaefc5f218dd307a0c90c4cdbddee71a39e8c9bf4530fa0` |
| `Master4_Grid_Maker_v2.0/System Files/Ready_To_Fly.ps1` | `58ab0bb86261c1d1c3820cd20353d6ca68b86e2bc0983eae09a7cbc4bdc90749` |

## PRAVE ME Tracker

Zip [`downloads/PRAVE_ME_Tracker_v1.zip`](https://github.com/Jim-dc95811/ArcGIS-Earth-Offline-Maps-Chartplotting/raw/c2b329a11863ef2cf20759685ab1be0aac27d6f8/downloads/PRAVE_ME_Tracker_v1.zip) (repository [ArcGIS-Earth-Offline-Maps-Chartplotting](https://github.com/Jim-dc95811/ArcGIS-Earth-Offline-Maps-Chartplotting)):

`90da6f2de2dcbedc2aa645244026597a45dbc2cd55de85e3d23071a2bd71f4cd`

| File | SHA-256 |
|---|---|
| `PRAVE_ME_Tracker_v2.0/PRAVE_ME_Tracker_User_Guide.pdf` | `8d4cc0a547b9694e135807a21a44d111fa9f991dcd67d2a7af09bc77c8e7c618` |
| `PRAVE_ME_Tracker_v2.0/START_TRACKER.bat` | `ac91ceb331770c01fa7661b12623883516423d1e8da88c07c699f39ee7abe3de` |
| `PRAVE_ME_Tracker_v2.0/System Files/PRAVE_ME_Tracker.py` | `5184c60ca552a79a0660e8969c83f20240a5f2d7b72e537aac38f8cb76271007` |
| `PRAVE_ME_Tracker_v2.0/System Files/Ready_To_Fly.ps1` | `58ab0bb86261c1d1c3820cd20353d6ca68b86e2bc0983eae09a7cbc4bdc90749` |

## PRAVE RMC Field Decoder Tester Gold

Zip [`downloads/PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold.zip`](https://github.com/Jim-dc95811/ArcGIS-Earth-Offline-Maps-Chartplotting/raw/c2b329a11863ef2cf20759685ab1be0aac27d6f8/downloads/PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold.zip) (repository [ArcGIS-Earth-Offline-Maps-Chartplotting](https://github.com/Jim-dc95811/ArcGIS-Earth-Offline-Maps-Chartplotting)):

`5bd882c79dd8fd5a94beb4e5c6a27e6d3a9aaeb7ac65b02f61a0257536e58fb9`

| File | SHA-256 |
|---|---|
| `PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold/System Files/PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold_Instructions.pdf` | `aa03d444e71290ae41a45f404707f71f6307416aeb50fdf1c2a735287658e5e9` |
| `PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold/System Files/Ready_To_Fly.ps1` | `58ab0bb86261c1d1c3820cd20353d6ca68b86e2bc0983eae09a7cbc4bdc90749` |
| `PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold/System Files/PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold.py` | `64f8ae1a73f794b793fd8a864ce580d8c9c9e3010e85b1ba5ee3129413b8e775` |
| `PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold/Run_PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold.bat` | `ff7f5491b5439804300dfb2c9723dc78ab80c70a435be93a04a3f1b1968722bf` |
| `PRAVE_RMC_Field_Decoder_Tester_v1_0_Gold/PRAVE_RMC_Field_Decoder_Tester_User_Manual.pdf` | `f75be01bbe86d0f50a72b6b50358bf72061cd88e770ad7045650c8e270272830` |

## TPKX Batch Factory

Zip [`downloads/TPKX_Batch_Factory_v1.zip`](https://github.com/Jim-dc95811/ArcGIS-Earth-Offline-Maps-Chartplotting/raw/c2b329a11863ef2cf20759685ab1be0aac27d6f8/downloads/TPKX_Batch_Factory_v1.zip) (repository [ArcGIS-Earth-Offline-Maps-Chartplotting](https://github.com/Jim-dc95811/ArcGIS-Earth-Offline-Maps-Chartplotting)):

`48850b3a511f02da248167a72917d7c1042ad9ed0b8e94056907ebea29bb03aa`

| File | SHA-256 |
|---|---|
| `TPKX_Batch_Factory_v2.0/BUILD_INSTALL.bat` | `e823c7e54459c6c85e1d4e957d61bd93a4de3a45f91400a8c6f23acc00637bd1` |
| `TPKX_Batch_Factory_v2.0/System Files/ArcGIS_TPKX_Factory.csproj` | `df6c8951b18f71f543abb982bfa9433098c327bd487054ac467a7f9a77e73127` |
| `TPKX_Batch_Factory_v2.0/System Files/BUILD_QUIET.ps1` | `de45963626c453617237fbb551664000e01fb726b3f486ade3e82e2158146a79` |
| `TPKX_Batch_Factory_v2.0/System Files/BUILD_QUIET.vbs` | `03a0f8e0e2aca7ce434040deee15a6a7f499c8f341a57eda8ec9e795bf6c3c11` |
| `TPKX_Batch_Factory_v2.0/System Files/BatchWindow.xaml` | `fced81a6e5964b70902fca010681548e31edc994ee66719675baea9662dac744` |
| `TPKX_Batch_Factory_v2.0/System Files/BatchWindow.xaml.cs` | `3b37c431bab5ca84ca2a7bbf252a88876d18153245a890fff855e808587c6217` |
| `TPKX_Batch_Factory_v2.0/System Files/Config.daml` | `d41a4f755e8d9d7bb0d240a4988ffbd560b4b04116bcf28427ff7f3a49a8af98` |
| `TPKX_Batch_Factory_v2.0/System Files/Images/Factory16.png` | `25bdc0e9860e0ccac395ffb4aa599507aba3e3fc2652cb1cde8ad9e8ea2e987f` |
| `TPKX_Batch_Factory_v2.0/System Files/Images/Factory32.png` | `05c6923b91fc12c6d5229c34fa7bdc3303fba25d1ca5de00836051abe0692686` |
| `TPKX_Batch_Factory_v2.0/System Files/Module1.cs` | `503c628e704f47055924f5d0ffd85b80ff1e130f533dd5e394e7ae4dc76ceb2c` |
| `TPKX_Batch_Factory_v2.0/System Files/OpenFactoryButton.cs` | `87c410655aa4c5be009a9d9f691c64186987eee1eb9c16d99545d8234b75cf02` |
| `TPKX_Batch_Factory_v2.0/System Files/QUIET_BUILD_NOTE.txt` | `c5013e12d96a6d99850caea586ed14b0ad63c5f33985ff940b12fe55cf13d9d2` |
| `TPKX_Batch_Factory_v2.0/System Files/README_GUI_TEST.txt` | `de3c09241979a1de6d3758df7a5e3abc985a5d51d88a5fb44d4651c5635f8ba0` |
| `TPKX_Batch_Factory_v2.0/TPKX_Batch_Factory_User_Guide.pdf` | `4cf60395fd4c1219cd1d9f61bf7474f5f559bdf5842a1cbb1e0e2fd327788af9` |

## EarthStick

Zip [`releases/EarthStick_v2.0.zip`](https://github.com/Jim-dc95811/EarthStick/raw/d54e3a132f1e2699e627f027562def0a789b196b/releases/EarthStick_v2.0.zip) (repository [EarthStick](https://github.com/Jim-dc95811/EarthStick)):

`e6f9dab82e87867e256eb3aba6db489ad3ba0971807481a4a2c04f2759a724da`

| File | SHA-256 |
|---|---|
| `EarthStick_v2.0/City_Beacons/01_Beacon_v2_Jacksonville.kmz` | `4e7f97a054bd52fcf59b7c17296bfef3500da175e277a4c0efe8b7b357c0d5bc` |
| `EarthStick_v2.0/City_Beacons/02_Beacon_v2_Atlanta.kmz` | `5313cb84de473980aea214b01e8cb6c02038d2e10dfdf6338af47fde78b2e491` |
| `EarthStick_v2.0/City_Beacons/03_Beacon_v2_New_York.kmz` | `0d4b7634bc0dd63935d9937a112451830044890db3599d9d8c24ece3e96d2d99` |
| `EarthStick_v2.0/City_Beacons/04_Beacon_v2_London.kmz` | `fd5425b5117b3108e79103f70899f587799220a029a845ccdcc8701555a52f2a` |
| `EarthStick_v2.0/City_Beacons/05_Beacon_v2_Paris.kmz` | `e5c06c0106972d961d27bce40b90d78b89419a573d53f1f4d3be67a4c3d66049` |
| `EarthStick_v2.0/City_Beacons/06_Beacon_v2_Rome.kmz` | `f528c8265011e3c4298687d86ebac40605cdcd512765e2a805df829a95886664` |
| `EarthStick_v2.0/City_Beacons/07_Beacon_v2_Tokyo.kmz` | `9ac2b522d1f8af0841085d6816210b860933a9e477e210b1db16dc3683fa297e` |
| `EarthStick_v2.0/City_Beacons/08_Beacon_v2_Sydney.kmz` | `79109df7448d15cf73aa2548031ae7b9b5a3ded298819de0113fb3cc4e5ca0a1` |
| `EarthStick_v2.0/City_Beacons/09_Beacon_v2_Rio_de_Janeiro.kmz` | `a5a066d808a8bb92a9984f8fc42dd2afb5edca9c4297dba5c7a262fe5fb7d154` |
| `EarthStick_v2.0/EarthStick_User_Guide.pdf` | `237ccbcb0b0dc1bac90a0e9906130c8516f7b192acf01e3de428787b8376fd67` |
| `EarthStick_v2.0/Fly_ArcGIS_Earth.bat` | `9f8e0faabeb739f45a2915de7d183a0fde77b82a4cb1f0858edc5a2fa5c3541e` |
| `EarthStick_v2.0/Gates/World_Gates_JAX_ATL_v21.kmz` | `df42e344317e1abaa7d40a9a659ab579fe1ed38e825273d708a88ba56e228d94` |
| `EarthStick_v2.0/System Files/EarthStick.bat` | `5a6515a07bade1d65507c322b3f2a0066c4b43d9059e180cb7ee958bcaa8809f` |
| `EarthStick_v2.0/System Files/EarthStick.py` | `d4dd56b38e8d43660dc51e184af49136d2916853bf31e03c318c6059d432e1f5` |
| `EarthStick_v2.0/System Files/Make_Taskbar_Shortcut.bat` | `57ae4c98931ca5427569a58419243412bf29cc08b0e1fa557227657ffeb3c72d` |
| `EarthStick_v2.0/System Files/Ready_To_Fly.ps1` | `58ab0bb86261c1d1c3820cd20353d6ca68b86e2bc0983eae09a7cbc4bdc90749` |
| `EarthStick_v2.0/System Files/gate_dropper.py` | `88ddc4d80ed880bddb55576a9b2e2f247b0b84aa41793e5fc9926fbe7cd9d7e5` |

## World Gate Maker

Zip [`releases/World_Gate_Maker_v2.0.zip`](https://github.com/Jim-dc95811/EarthStick/raw/d54e3a132f1e2699e627f027562def0a789b196b/releases/World_Gate_Maker_v2.0.zip) (repository [EarthStick](https://github.com/Jim-dc95811/EarthStick)):

`50dff90f7c74bf38896f6fea1be574878472da4a80bd5e5fdf16a12f6a81285a`

| File | SHA-256 |
|---|---|
| `World_Gate_Maker_v2.0/System Files/Ready_To_Fly.ps1` | `58ab0bb86261c1d1c3820cd20353d6ca68b86e2bc0983eae09a7cbc4bdc90749` |
| `World_Gate_Maker_v2.0/System Files/World_Gate_Maker.py` | `7a57a4d17931ba3c0b94939229a42f71824e3fc578d230e5b54c7028290c6ef4` |
| `World_Gate_Maker_v2.0/World_Gate_Maker.bat` | `3addbb4ac95c1c6877a7ee12a1d3c25643ca463954e5be406b1b2cc2be3b75cf` |
| `World_Gate_Maker_v2.0/World_Gate_Maker_User_Manual.pdf` | `2c6bcd396b848f77d0b153e7a504595a8903ba00bb355b3a8842c1ab87aad458` |

## Object Factory

Zip [`releases/ArcGIS_Earth_Object_Factory_v2.0.zip`](https://github.com/Jim-dc95811/ArcGIS-Earth-Object-Factory/raw/2b86893f368c0ed4babbc59acc3c216a327fc9b3/releases/ArcGIS_Earth_Object_Factory_v2.0.zip) (repository [ArcGIS-Earth-Object-Factory](https://github.com/Jim-dc95811/ArcGIS-Earth-Object-Factory)):

`607e34a1bb8928b707e15ef4ac9821493ae45b9f93c6c70e14161b79f71a5659`

| File | SHA-256 |
|---|---|
| `Object_Factory_v2.0/ArcGIS_Earth_Object_Factory_v2.0_User_Manual.pdf` | `7c8bcc6fa6be1a595c34d3e75f022fc25db84731d7282c97af2b6635f4fbc1ed` |
| `Object_Factory_v2.0/Run_Object_Factory.bat` | `b47e3ce633e538dc6477585780b8e9f7677f90bbc2592a5bc25d696bddc4a1ce` |
| `Object_Factory_v2.0/System Files/Object_Factory_v2.0.py` | `34f6a670ccf48873140a6e198bbf95b48d8ba04ffc0033b5b2f600d346f7f9a8` |
| `Object_Factory_v2.0/System Files/Ready_To_Fly.ps1` | `58ab0bb86261c1d1c3820cd20353d6ca68b86e2bc0983eae09a7cbc4bdc90749` |
| `Object_Factory_v2.0/System Files/SAMPLE_Beacon.kml` | `956bc130c832ddfd434b63a6be588dcc75bcde67ceda3c1fb75cbcf9010fa635` |
| `Object_Factory_v2.0/System Files/SAMPLE_Linked_Camera.kmz` | `bd49774c08ff12128b76d755b2452213b870aa77f2308a3d59c7128059b56c20` |
| `Object_Factory_v2.0/System Files/SAMPLE_Object_Set.kmz` | `a87c9782cbaab2f780809570d7dbdb2f137c7b06a20b89dbff3b5bbc106f4917` |
| `Object_Factory_v2.0/System Files/SAMPLE_Sky_Compass.kmz` | `e9ec5f74d42af97758d31dade89bd28a693ed53ce415bb75df4299767c56778e` |
| `Object_Factory_v2.0/System Files/icons/E.png` | `d121eadd22d0ca1bf65d5d4134d36c65ad2c3525ce6db76297e67c28b2006d9d` |
| `Object_Factory_v2.0/System Files/icons/N.png` | `5068fad4a5f924f40b3d9b5a7ad1e967e32ef254088c563695138ed8eb9cfbcc` |
| `Object_Factory_v2.0/System Files/icons/S.png` | `53d3344d5703a9b5679a60d079d00717e6f2a9c14a6b1b384a347e47f32c93ee` |
| `Object_Factory_v2.0/System Files/icons/W.png` | `f2685cb071019bc33809f689db64a716af9d4c9738d7f1861ac5488d62980d5d` |
| `Object_Factory_v2.0/System Files/icons/bird.png` | `945d678fd65ac63ce6021c5758a818304aeb71c68eaf0a5f5d53e1cda05195ed` |
| `Object_Factory_v2.0/System Files/icons/camera.png` | `052281d5514de26ed8a6f65067651388e80befd16cc91f5da23b8c80fe2cd513` |
| `Object_Factory_v2.0/System Files/icons/firetruck.png` | `5aa7b3518166bcf8fcb781e445fc2a27f0e4c1ecb2da3556837f732079aabad1` |
| `Object_Factory_v2.0/System Files/icons/fuel.png` | `67459f140580cd3a5d33d1b2be797b3b3e62a390a3a260f8da775957963f87bb` |
| `Object_Factory_v2.0/System Files/icons/hazard.png` | `87593e79716d981e85c8b62ca26fe6d36751f2b32c318ca769e17e5553bec414` |
| `Object_Factory_v2.0/System Files/icons/helicopter.png` | `0b0da3d7b4f15284930e01f0c2bc87bed9bec633990cb658fca579067aeb79e1` |
| `Object_Factory_v2.0/System Files/icons/home.png` | `8b82756d82d3077158374fa66e5b2f0dd1d7aab1083f2b1b8c857cafa8b59ccb` |
| `Object_Factory_v2.0/System Files/icons/medical.png` | `1074e4592318539a9c57f4c93ccdc61e9cf053bbfc974b72f17bd60306dcfa59` |
| `Object_Factory_v2.0/System Files/icons/object.png` | `f4259bbf1999e835706a9b8bbc053c219f62f0e4d7423b15cbb656d4f5a010e9` |
| `Object_Factory_v2.0/System Files/icons/staging.png` | `4e0e5685d48c651665229dc3bc65fff466db8e34c3935b707f27a91add07d2cd` |
| `Object_Factory_v2.0/System Files/icons/water.png` | `e6fd1d7bb3c3de45bc5bb44a5fb410d8fc1c279c1d949ce9e94823a2d0e087c7` |
| `Object_Factory_v2.0/System Files/sample_objects.txt` | `0cc672ead86c21247adf3f4ab76b005a16cb7abfdf53d2f63c9648655fb85540` |
| `Object_Factory_v2.0/System Files/simple_objects.txt` | `6d1bbd1a7eee393ee89a04857c533b7aed327c17e0abc4fbd6c5839edc1f1bc8` |

## PointLayer

Zip [`releases/PointLayer_v2.0.zip`](https://github.com/Jim-dc95811/Point-Maps/raw/80a9c0a5d3eaebdbd9bf57209888a71e26074a69/releases/PointLayer_v2.0.zip) (repository [Point-Maps](https://github.com/Jim-dc95811/Point-Maps)):

`ebe0562755f32231b2a98064fb3e537011fc591869db230819847894c125a2d5`

| File | SHA-256 |
|---|---|
| `PointLayer_v2.0/PointLayer.bat` | `8eb30a643a631ff87e10684b49e0b5147932e66ec06a635be3a1a06cf043f212` |
| `PointLayer_v2.0/PointLayer_User_Guide.pdf` | `29a4a152721e8c12ec384b1f1546b23930c4b1ae719e4ddd0731082b0ec7e371` |
| `PointLayer_v2.0/System Files/PointLayer.py` | `bb89c54955d8ff4029288bd4f5f817f2da81e8548827226303f2acd68323ecec` |
| `PointLayer_v2.0/System Files/Ready_To_Fly.ps1` | `58ab0bb86261c1d1c3820cd20353d6ca68b86e2bc0983eae09a7cbc4bdc90749` |

## Parcel100

Zip [`downloads/Parcel100_v2.0.zip`](https://github.com/Jim-dc95811/Parcel100/raw/2428eef41fa36018ec7a5a8289eed254d05ed50c/downloads/Parcel100_v2.0.zip) (repository [Parcel100](https://github.com/Jim-dc95811/Parcel100)):

`9f6066bd03306f03d9faa7d3a3afbc94055e6845c2a5cc25d3a64d31d0b6ee59`  *(rebuilt by the repository's GitHub workflow - check the files inside)*

| File | SHA-256 |
|---|---|
| `Parcel100_v2.0/Parcel100.bat` | `0807f5e73ae1004ea6f9945fae88e6b6386bdfdff40376d588ea928246d28c31` |
| `Parcel100_v2.0/Parcel100_User_Manual.pdf` | `a6b8133aa6c3833a7948be2246a1f9044957cdd189b083db3c0cb3cd79df545d` |
| `Parcel100_v2.0/System Files/Parcel100.py` | `fdcae292e3a979b2c6cac5afd3c62757d5505d4d35a691b0eec46bd96e6a1019` |
| `Parcel100_v2.0/System Files/Ready_To_Fly.ps1` | `58ab0bb86261c1d1c3820cd20353d6ca68b86e2bc0983eae09a7cbc4bdc90749` |

## Picture World Maker

Zip [`releases/Picture_World_Maker_v2.0.zip`](https://github.com/Jim-dc95811/Picture-World-Maker/raw/b164827bc8b77c7464977d7ef0e7c4a9b7ab802d/releases/Picture_World_Maker_v2.0.zip) (repository [Picture-World-Maker](https://github.com/Jim-dc95811/Picture-World-Maker)):

`ee0d2229ee130bf0069c8da2efb791312bd00a22e92a3892c967ba79022ebbf9`

| File | SHA-256 |
|---|---|
| `Picture_World_Maker_v2.0/Picture_World_Maker_User_Manual.pdf` | `ccff7ac77aa9f1934c834582b8b6879627ac3c79e3af7995603c0db1f2310c97` |
| `Picture_World_Maker_v2.0/Start Picture World Maker.bat` | `82e8f2ebcd88fb1b011cc4aedd1f5b1d4b1749885535020fe3f2d9a6b8482b31` |
| `Picture_World_Maker_v2.0/System Files/MBTiles_to_TPKX_v0_3_0.py` | `9fbdd81d4114cddcc99616f465d182b767cc00d26601bba142fad620d3df9dce` |
| `Picture_World_Maker_v2.0/System Files/PICTURE_WORLD_MAKER.py` | `2d263211db31641157d770795a8f232fec536b7bf685465c80588101586b3c1d` |
| `Picture_World_Maker_v2.0/System Files/PWM_PHOTO_TILER.py` | `e15e40b80aa2454d0d5860eb4bcc64c4ba4867b020ae13af9285bba0dad50de8` |
| `Picture_World_Maker_v2.0/System Files/PWM_PIPELINE.py` | `3de1f0b20bcccdec52f3b0cdb5a398f085c20a52677fe8dcd26efd2ef52487f4` |
| `Picture_World_Maker_v2.0/System Files/PWM_SELF_TEST.py` | `380a0538c9ae9618f380f449a52e1191464344607e2447d1ad72d34051d7b814` |
| `Picture_World_Maker_v2.0/System Files/Picture_World_Maker_Config.ini` | `76bea47dc9978ffdd8ae1f008c1b8a724afddc086fa94244605a5df63958e557` |
| `Picture_World_Maker_v2.0/System Files/Ready_To_Fly.ps1` | `58ab0bb86261c1d1c3820cd20353d6ca68b86e2bc0983eae09a7cbc4bdc90749` |
| `Picture_World_Maker_v2.0/System Files/START PICTURE WORLD MAKER.pyw` | `d25a8c7654a8bab6aab5d2b7ffe15c5072f107388fafc1aec680f303a74e9818` |

Written by `tools/make_reference.py`.
