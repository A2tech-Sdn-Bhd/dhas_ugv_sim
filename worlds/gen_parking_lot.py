#!/usr/bin/env python3
"""
Generate a Gazebo Classic (gazebo11) SDF world file:
  parking_lot_world.world

Mimics an overhead satellite view of a massive vehicle storage lot
(like the one in the reference image) — no road lines, no parking lines,
just hundreds of cars packed in dense clusters on bare asphalt.

Car model used: prius_hybrid  (available on Gazebo Fuel / OSRF model DB)
  If you haven't downloaded it: gz model --download prius_hybrid
  Or substitute with any car SDF model path you have locally.
"""

import math
import random
import sys

random.seed(42)

# ---------------------------------------------------------------------------
# Car dimensions (Prius ~4.5 m long, ~1.85 m wide)
# ---------------------------------------------------------------------------
CAR_L  = 4.5    # length along X when yaw=0
CAR_W  = 1.85   # width  along Y when yaw=0
GAP_FR = 0.35   # front-rear gap between cars
GAP_LR = 0.30   # left-right gap between cars

def grid_spacing(yaw_deg: float):
    """Return (dx, dy) step sizes for a grid at given yaw."""
    a = abs(yaw_deg % 180)
    if a < 45 or a > 135:           # roughly east-west orientation
        return CAR_L + GAP_FR, CAR_W + GAP_LR
    else:                           # roughly north-south orientation
        return CAR_W + GAP_LR, CAR_L + GAP_FR

def gen_cluster(base_x, base_y, rows, cols,
                yaw_deg=0.0, jitter=0.15):
    """Return list of (x, y, yaw_radians) tuples for a dense car cluster."""
    sx, sy = grid_spacing(yaw_deg)
    cars = []
    for r in range(rows):
        for c in range(cols):
            x = base_x + c * sx + random.uniform(-jitter, jitter)
            y = base_y + r * sy + random.uniform(-jitter, jitter)
            yaw = math.radians(yaw_deg + random.uniform(-4, 4))
            cars.append((x, y, yaw))
    return cars

# ---------------------------------------------------------------------------
# Build all car positions
# ---------------------------------------------------------------------------
all_cars = []

# ── TOP SECTION: diagonal chevron rows (cars on transporters / just unloaded)
for i in range(14):
    bx = -75 + i * 11.0
    cluster = gen_cluster(bx, 48, rows=2, cols=3, yaw_deg=40, jitter=0.25)
    all_cars.extend(cluster)

for i in range(9):
    bx = -30 + i * 11.5
    cluster = gen_cluster(bx, 60, rows=2, cols=2, yaw_deg=-40, jitter=0.25)
    all_cars.extend(cluster)

# Top-right tight grid block
for r in range(7):
    for c in range(9):
        x = 70 + c * (CAR_W + GAP_LR)
        y = 44 + r * (CAR_L + GAP_FR)
        all_cars.append((x, y, 0.0))

# ── MIDDLE SECTION: massive dense car storage block
#    Multiple sub-clusters at slightly different orientations
middle_specs = [
    # (base_x, base_y, rows, cols, yaw_deg)
    (-80, -5,  12, 8,   0),
    (-44, -5,  12, 7,   0),
    (-10, -5,  12, 8,   0),
    ( 28, -5,  12, 7,   0),
    ( 62, -5,  12, 8,   0),
    # offset row below
    (-80, -58, 10, 8,   0),
    (-43, -58, 10, 7,   0),
    ( -8, -58, 10, 8,   0),
    ( 29, -58, 10, 7,   0),
    ( 64, -58, 10, 7,   0),
    # 90-degree groups scattered in gaps
    (-62,  16,  6, 5,  90),
    (-27,  16,  6, 5,  90),
    (  8,  16,  6, 5,  90),
    ( 44,  16,  6, 5,  90),
    (-62, -30,  7, 5,  90),
    (-26, -30,  7, 5,  90),
    (  9, -30,  7, 5,  90),
    ( 45, -30,  7, 5,  90),
    # Extra fill
    (-72, -80,  4, 6,   0),
    (-45, -80,  4, 5,   0),
    (-18, -80,  4, 6,   0),
    (  8, -80,  4, 5,   0),
    ( 33, -80,  4, 5,   0),
]

for (bx, by, rows, cols, yd) in middle_specs:
    cluster = gen_cluster(bx, by, rows=rows, cols=cols,
                          yaw_deg=yd, jitter=0.30)
    all_cars.extend(cluster)

# ── BOTTOM PARTIAL ROWS
for i in range(7):
    bx = -50 + i * 15.5
    cluster = gen_cluster(bx, -95, rows=3, cols=4, yaw_deg=0, jitter=0.2)
    all_cars.extend(cluster)

print(f"[gen] Total cars to place: {len(all_cars)}", file=sys.stderr)

# ---------------------------------------------------------------------------
# Car colour alternation (simulate mixed colours visible in image)
# ---------------------------------------------------------------------------
# Available Gazebo Fuel cars (common ones):
#   prius_hybrid          – white/silver
# For colour variety we'll use the same model but vary the static colour
# via material tags, OR reference multiple models:
#   model://prius_hybrid
#   model://vehicle_blue   (if available)
#   model://vehicle_red    (if available)
# We'll embed lightweight box-based car proxies AS WELL as a note to swap
# in the real model URI.

# Actually — let's produce BOTH:
#   1. An SDF that includes inline simplified car meshes so it works out-of-the-box
#   2. A comment showing how to swap to prius_hybrid once you have Fuel models

# ---------------------------------------------------------------------------
# SDF Generation
# ---------------------------------------------------------------------------

HEADER = """\
<?xml version="1.0" ?>
<!--
  Gazebo Classic (gazebo 11) world — Dense Vehicle Storage Lot
  ============================================================
  Mimics the satellite-view of a car marshalling yard / port storage lot.

  HOW TO USE
  ----------
  1. Copy this file to your ROS/Gazebo workspace:
       cp parking_lot_world.world ~/catkin_ws/src/my_pkg/worlds/

  2. Launch with Gazebo:
       gazebo parking_lot_world.world

  3. (Optional) For high-fidelity Prius models, install from Fuel:
       gz fuel download --url https://fuel.gazebosim.org/1.0/OpenRobotics/models/Prius%20Hybrid
     Then replace every <uri>model://car_box_*</uri> with:
       <uri>model://Prius Hybrid</uri>

  NOTES
  -----
  - Ground plane has NO road markings or parking lines.
  - Cars are placed in dense irregular clusters matching the reference image.
  - Each car is a static model (no physics / joints needed for a static lot).
  - Sun + ambient light configured for overhead daylight rendering.
-->
<sdf version="1.6">
  <world name="parking_lot">

    <!-- ═══════════════════ PHYSICS ═══════════════════ -->
    <physics type="ode">
      <real_time_update_rate>1000</real_time_update_rate>
      <max_step_size>0.001</max_step_size>
    </physics>

    <!-- ═══════════════════ SCENE ════════════════════ -->
    <scene>
      <sky>
        <clouds>
          <speed>12</speed>
        </clouds>
      </sky>
      <ambient>0.7 0.7 0.7 1</ambient>
      <background>0.55 0.55 0.58 1</background>
      <shadows>false</shadows>
    </scene>

    <!-- ═══════════════════ SUN ══════════════════════ -->
    <light name="sun" type="directional">
      <cast_shadows>false</cast_shadows>
      <pose>0 0 100 0 -0 0</pose>
      <diffuse>0.9 0.9 0.85 1</diffuse>
      <specular>0.3 0.3 0.3 1</specular>
      <direction>-0.3 0.2 -0.9</direction>
    </light>

    <!-- ═══════════════════ GROUND PLANE (bare asphalt) ══════════════════ -->
    <model name="ground_plane">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>400 300</size>
            </plane>
          </geometry>
          <surface>
            <friction><ode><mu>0.8</mu><mu2>0.8</mu2></ode></friction>
          </surface>
        </collision>
        <visual name="visual">
          <cast_shadows>false</cast_shadows>
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>400 300</size>
            </plane>
          </geometry>
          <material>
            <script>
              <uri>file://media/materials/scripts/gazebo.material</uri>
              <name>Gazebo/Grey</name>
            </script>
            <!-- Asphalt-grey colour override -->
            <ambient>0.28 0.28 0.27 1</ambient>
            <diffuse>0.32 0.32 0.30 1</diffuse>
            <specular>0.01 0.01 0.01 1</specular>
          </material>
        </visual>
      </link>
    </model>

    <!-- ═══════════════════ CAR MODEL DEFINITIONS ════════════════════════
         We define 4 reusable car appearance variants as inline models.
         Body: box 4.45 × 1.80 × 0.55 m  (sedan silhouette)
         Roof: box 1.80 × 1.40 × 0.40 m  (cabin)
         Wheels: 4 cylinders r=0.32 h=0.22
         All static (no joints/physics).
    ════════════════════════════════════════════════════════════════════ -->
"""

# We'll define car colours
COLOURS = [
    # (name_suffix, body_diffuse, roof_diffuse)
    ("white",   "0.92 0.92 0.92 1", "0.88 0.88 0.88 1"),
    ("silver",  "0.70 0.70 0.72 1", "0.65 0.65 0.67 1"),
    ("red",     "0.78 0.12 0.10 1", "0.65 0.10 0.08 1"),
    ("black",   "0.12 0.12 0.12 1", "0.08 0.08 0.08 1"),
    ("blue",    "0.15 0.30 0.72 1", "0.10 0.22 0.60 1"),
    ("beige",   "0.82 0.75 0.60 1", "0.72 0.66 0.52 1"),
]

def car_model_def(colour_name, body_diff, roof_diff):
    """Return an SDF <model> block for one car colour variant (for include)."""
    # We generate a self-contained model so it can be INCLUDED in the world
    # Actually for inline models we just build the link geometry directly per instance.
    pass  # we'll inline each car directly

def car_instance_sdf(idx, x, y, yaw_rad, colour_idx):
    name = f"car_{idx:04d}"
    cd = COLOURS[colour_idx]
    body_diff = cd[1]
    roof_diff = cd[2]

    # wheel positions (relative to car centre, car points +X)
    WR = 0.32   # wheel radius
    WH = 0.22   # wheel half-width
    WBx = 1.45  # wheelbase half (front/rear)
    WBy = 0.85  # track half (left/right)
    WZ  = WR    # wheel centre height

    yaw_deg = math.degrees(yaw_rad)

    return f"""
    <model name="{name}">
      <static>true</static>
      <pose>{x:.3f} {y:.3f} 0 0 0 {yaw_rad:.4f}</pose>

      <!-- Body -->
      <link name="body">
        <visual name="body_vis">
          <pose>0 0 0.55 0 0 0</pose>
          <geometry><box><size>4.45 1.80 0.55</size></box></geometry>
          <material>
            <ambient>0.15 0.15 0.15 1</ambient>
            <diffuse>{body_diff}</diffuse>
            <specular>0.4 0.4 0.4 1</specular>
          </material>
        </visual>
        <!-- Cabin/roof -->
        <visual name="roof_vis">
          <pose>0.10 0 1.12 0 0 0</pose>
          <geometry><box><size>2.10 1.40 0.40</size></box></geometry>
          <material>
            <ambient>0.10 0.10 0.10 1</ambient>
            <diffuse>{roof_diff}</diffuse>
            <specular>0.5 0.5 0.5 1</specular>
          </material>
        </visual>
        <!-- Windscreen tint -->
        <visual name="glass_f">
          <pose>1.02 0 0.95 0 -0.45 0</pose>
          <geometry><box><size>0.05 1.35 0.38</size></box></geometry>
          <material><diffuse>0.50 0.60 0.70 0.6</diffuse></material>
        </visual>
        <!-- Front bumper -->
        <visual name="bumper_f">
          <pose>2.28 0 0.42 0 0 0</pose>
          <geometry><box><size>0.12 1.72 0.28</size></box></geometry>
          <material><diffuse>0.18 0.18 0.18 1</diffuse></material>
        </visual>
        <!-- Rear bumper -->
        <visual name="bumper_r">
          <pose>-2.28 0 0.42 0 0 0</pose>
          <geometry><box><size>0.12 1.72 0.28</size></box></geometry>
          <material><diffuse>0.18 0.18 0.18 1</diffuse></material>
        </visual>
        <!-- Wheels (4) -->
        <visual name="wfl">
          <pose>{WBx:.2f} {WBy:.2f} {WZ:.2f} 1.5708 0 0</pose>
          <geometry><cylinder><radius>{WR}</radius><length>{WH*2:.2f}</length></cylinder></geometry>
          <material><diffuse>0.08 0.08 0.08 1</diffuse></material>
        </visual>
        <visual name="wfr">
          <pose>{WBx:.2f} {-WBy:.2f} {WZ:.2f} 1.5708 0 0</pose>
          <geometry><cylinder><radius>{WR}</radius><length>{WH*2:.2f}</length></cylinder></geometry>
          <material><diffuse>0.08 0.08 0.08 1</diffuse></material>
        </visual>
        <visual name="wrl">
          <pose>{-WBx:.2f} {WBy:.2f} {WZ:.2f} 1.5708 0 0</pose>
          <geometry><cylinder><radius>{WR}</radius><length>{WH*2:.2f}</length></cylinder></geometry>
          <material><diffuse>0.08 0.08 0.08 1</diffuse></material>
        </visual>
        <visual name="wrr">
          <pose>{-WBx:.2f} {-WBy:.2f} {WZ:.2f} 1.5708 0 0</pose>
          <geometry><cylinder><radius>{WR}</radius><length>{WH*2:.2f}</length></cylinder></geometry>
          <material><diffuse>0.08 0.08 0.08 1</diffuse></material>
        </visual>
        <!-- Collision (simplified box) -->
        <collision name="col">
          <pose>0 0 0.55 0 0 0</pose>
          <geometry><box><size>4.45 1.80 1.30</size></box></geometry>
        </collision>
      </link>
    </model>"""


FOOTER = """
    <!-- GUI camera: top-down aerial view -->
    <gui fullscreen="0">
      <camera name="user_camera">
        <pose>0 0 200 0 1.5707 0</pose>
        <view_controller>orbit</view_controller>
        <projection_type>orthographic</projection_type>
      </camera>
    </gui>

  </world>
</sdf>
"""

# ---------------------------------------------------------------------------
# Write the world file
# ---------------------------------------------------------------------------
out_path = "/mnt/user-data/outputs/parking_lot_world.world"

with open(out_path, "w") as f:
    f.write(HEADER)

    for idx, (x, y, yaw) in enumerate(all_cars):
        # Assign colour: bias toward white/silver (like the image)
        r = random.random()
        if r < 0.35:
            cidx = 0   # white
        elif r < 0.60:
            cidx = 1   # silver
        elif r < 0.72:
            cidx = 2   # red
        elif r < 0.82:
            cidx = 3   # black
        elif r < 0.92:
            cidx = 4   # blue
        else:
            cidx = 5   # beige
        f.write(car_instance_sdf(idx, x, y, yaw, cidx))

    f.write(FOOTER)

print(f"[gen] World written to {out_path}", file=sys.stderr)
print(f"[gen] Cars placed: {len(all_cars)}", file=sys.stderr)
print(f"[gen] File size: {__import__('os').path.getsize(out_path)/1024/1024:.2f} MB",
      file=sys.stderr)
