# Video to Foot Traffic: Oculus Train Hall Case Study

**Status: Shell.** Structure and pipeline are here; working code is not yet built.

## What you will build

A Python pipeline that takes a video of people moving through the Oculus (or any indoor space) and produces:

- A CSV of per-person tracks over time
- A GeoJSON or projected CSV in the coordinate system of a Rhino model of the space
- An animation that plays back the traffic over the space

Deliverables can be imported to Rhino via Grasshopper (CSV to points to curves), or fed to a web-based animation (D3, three.js).

## Prerequisites

- Python 3.10+, ideally in a conda or venv
- A GPU for reasonable speed. CPU works for short clips but is slow.
- Rhino 7+ with Grasshopper if you want the Rhino target
- A source video. Public options:
  - Fixed-camera cuts you record on-site (best; you control the calibration)
  - CCTV archives you have permission to use
  - Public YouTube footage of the Oculus (verify licensing before publishing anything derived)

## The pipeline

```
video.mp4
   │
   ▼   YOLOv8 detection (persons only)
per-frame bounding boxes
   │
   ▼   ByteTrack or DeepSORT
per-person track IDs across frames
   │
   ▼   Homography projection
tracks in image coordinates  →  tracks in floor-plane coordinates
   │
   ▼   Export
tracks.csv   +   tracks.geojson   +   preview.mp4
```

## Required libraries

```bash
pip install ultralytics opencv-python numpy pandas shapely
```

Ultralytics ships YOLOv8 with built-in ByteTrack. No separate tracker install needed.

## Walkthrough (outline)

### 1. Detect and track people

```python
from ultralytics import YOLO
model = YOLO("yolov8n.pt")  # nano; use yolov8s or yolov8m for accuracy

results = model.track(
    source="oculus.mp4",
    classes=[0],           # 0 = person
    persist=True,
    tracker="bytetrack.yaml",
    save=True,
)
```

Each frame yields a list of detections with `xyxy` bounding boxes and a stable `id`.

### 2. Extract track records

Loop the results and record `{track_id, frame, timestamp, foot_x, foot_y}`. `foot_x` and `foot_y` are the midpoint of the bottom edge of the bounding box (approximates where the person is standing).

### 3. Calibrate the homography

The Oculus floor is a plane. Pick four points visible in the video whose real-world floor coordinates you know (measure from the Rhino model, or from Santiago Calatrava's construction drawings). Use `cv2.findHomography` to compute the pixel-to-floor transform.

```python
H, _ = cv2.findHomography(src_pts, dst_pts)  # both Nx2 arrays
```

Apply `H` to each `(foot_x, foot_y)` to get `(floor_x, floor_y)` in your Rhino coordinate system.

### 4. Export

Write `tracks.csv` with columns `track_id, frame, t_seconds, floor_x, floor_y`. That is enough for Grasshopper.

Also write `tracks.geojson` if you want to overlay on a web map:

```python
import geopandas as gpd
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.floor_x, df.floor_y))
gdf.to_file("tracks.geojson", driver="GeoJSON")
```

### 5. Import to Rhino

In Grasshopper:
- **Read File** or **Import CSV** to load the tracks
- Group by `track_id`
- Build a `Polyline` per track from the sorted floor coordinates
- Optionally, animate by driving a slider tied to `t_seconds`

## Extensions

- **Density heatmap.** Grid the floor, count track points per cell per time bin, render as a color mesh in Rhino or on a web canvas.
- **Speed and dwell.** Compute speed per track segment; flag stationary segments as dwells. Map dwell hotspots.
- **Group detection.** Cluster tracks that stay close and move together.
- **Occlusion recovery.** DeepSORT with an appearance model handles crossings and occlusions better than ByteTrack alone.

## Ethical considerations

- **Faces.** Do not save or share face crops. YOLO's person detection does not extract faces, but if you visualize frames, blur them.
- **Consent and location.** Public spaces are generally legal to observe, but publishing derived data can still be sensitive. Talk to your instructor before using material that could identify individuals.
- **IRB.** If this is research on human behavior for a publication, you likely need approval.

## Common pitfalls

- **Camera motion.** YOLO tracking assumes a fixed camera. Handheld video needs stabilization first (ffmpeg's `vidstab` filter).
- **Bad homography.** If your four calibration points are near-collinear or clustered, the transform is unstable. Spread them across the frame.
- **Lens distortion.** Wide-angle CCTV lenses distort. Undistort with a checkerboard calibration if you have one; otherwise stick to the center of the frame.
- **ID switching.** ByteTrack loses IDs across long occlusions. Post-process by stitching short tracks that end and begin near the same place at the same time.
- **File sizes.** A ten-minute 4K clip processed at 30 fps yields 18,000 frames. Downsample to 5 to 10 fps for tracking; you rarely need more.
