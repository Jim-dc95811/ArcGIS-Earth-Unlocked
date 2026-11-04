ArcGIS Earth Flight launcher v1.0
One click starts ArcGIS Earth, then EarthStick.

1. Copy Fly_ArcGIS_Earth.bat and Make_Taskbar_Shortcut.bat into your EarthStick folder
   (the folder with EarthStick.bat and EarthStick.py).
2. Double-click Make_Taskbar_Shortcut.bat once. It finds ArcGIS Earth and puts an
   "ArcGIS Earth Flight" shortcut (ArcGIS Earth icon) on your desktop.
3. Right-click the shortcut > Show more options > Pin to taskbar.

Clicking it starts ArcGIS Earth (unless it is already running), then EarthStick,
which waits until ArcGIS Earth is ready.

If ArcGIS Earth cannot be found: put its full .exe path (from your ArcGIS Earth
shortcut > Properties > Target) as the only line of ArcGIS_Earth_path.txt in the
EarthStick folder.
