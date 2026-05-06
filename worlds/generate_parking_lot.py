#!/usr/bin/env python3
"""Generate parking_lot.sdf with many cars parked in vertical columns.

Layout:
  - 2 columns of parked cars facing each other in each bay
  - 3 bays total (6 car columns), with driving lanes between bays and on the sides
  - 12 cars per column = 72 cars total
  - Cars are 4.5m x 2m x 1.5m
  - Driving lanes are ~5m wide
"""

import math
import random

random.seed(42)

OUTPUT = "/home/a2tech/Desktop/project/a2tech/dhas_ugv_sim/worlds/parking_lot.sdf"

# Car geometry
CAR_LENGTH = 4.5  # X
CAR_WIDTH = 2.0   # Y
CAR_HEIGHT = 1.5  # Z

# Column configuration: each bay has 2 columns close together (cars face the lane)
# Lane between bays is ~5m, lane on outer edges is ~4m
# X positions of column centers (from left to right)
# Each bay: 2 columns 5m apart (back-to-back parking, 0.5m gap between car edges)
# Between bays: 11m center-to-center (6.5m driving lane)
# Robot default spawn is at x=0,y=-2 which falls in the lane between Bay 3 and Bay 4
COLUMN_X = [-40.0, -35.0,   # Bay 1
            -24.0, -19.0,    # Bay 2
             -8.0,  -3.0,    # Bay 3 (lane center at ~X=2.5, so X=0 is in lane)
              8.0,  13.0,    # Bay 4
             24.0,  29.0]    # Bay 5

# Car Y positions (along each column)
CAR_Y = list(range(-18, 19, 4))  # 10 cars from -18 to +18

# Colors per column (make them distinguishable per bay)
COLUMN_COLORS = [
    # Bay 1: blues
    (0.2, 0.2, 0.7), (0.1, 0.3, 0.9),
    # Bay 2: reds
    (0.7, 0.2, 0.2), (0.9, 0.1, 0.1),
    # Bay 3: greens
    (0.2, 0.7, 0.2), (0.1, 0.8, 0.3),
    # Bay 4: silvers/grays with color tint
    (0.6, 0.6, 0.7), (0.5, 0.5, 0.8),
    # Bay 5: dark blues/purples
    (0.3, 0.2, 0.6), (0.2, 0.1, 0.7),
]

# Subtle per-car color variation
def vary_color(base, idx):
    r, g, b = base
    r = min(1.0, max(0.0, r + random.uniform(-0.08, 0.08)))
    g = min(1.0, max(0.0, g + random.uniform(-0.08, 0.08)))
    b = min(1.0, max(0.0, b + random.uniform(-0.08, 0.08)))
    return (r, g, b)


def generate_world():
    lines = []
    lines.append('<?xml version="1.0" ?>')
    lines.append('<sdf version="1.6">')
    lines.append('  <world name="parking_lot">')
    lines.append('')
    lines.append('    <physics name="1ms" type="ignored">')
    lines.append('      <max_step_size>0.001</max_step_size>')
    lines.append('      <real_time_factor>1.0</real_time_factor>')
    lines.append('    </physics>')
    lines.append('')
    lines.append('    <plugin filename="ignition-gazebo-contact-system" name="gz::sim::systems::Contact" />')
    lines.append('    <plugin filename="ignition-gazebo-imu-system" name="gz::sim::systems::Imu" />')
    lines.append('    <plugin filename="ignition-gazebo-physics-system" name="gz::sim::systems::Physics" />')
    lines.append('    <plugin filename="ignition-gazebo-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster" />')
    lines.append('    <plugin filename="ignition-gazebo-sensors-system" name="gz::sim::systems::Sensors" />')
    lines.append('    <plugin filename="ignition-gazebo-user-commands-system" name="gz::sim::systems::UserCommands" />')
    lines.append('')
    lines.append('    <spherical_coordinates>')
    lines.append('      <surface_model>EARTH_WGS84</surface_model>')
    lines.append('      <world_frame_orientation>ENU</world_frame_orientation>')
    lines.append('      <latitude_deg>50.088384</latitude_deg>')
    lines.append('      <longitude_deg>19.939128</longitude_deg>')
    lines.append('      <elevation>0</elevation>')
    lines.append('      <heading_deg>0</heading_deg>')
    lines.append('    </spherical_coordinates>')
    lines.append('')
    lines.append('    <light type="directional" name="sun">')
    lines.append('      <cast_shadows>true</cast_shadows>')
    lines.append('      <pose>0 0 10 0 0 0</pose>')
    lines.append('      <diffuse>0.8 0.8 0.8 1</diffuse>')
    lines.append('      <specular>0.2 0.2 0.2 1</specular>')
    lines.append('      <attenuation>')
    lines.append('        <range>1000</range>')
    lines.append('        <constant>0.9</constant>')
    lines.append('        <linear>0.01</linear>')
    lines.append('        <quadratic>0.001</quadratic>')
    lines.append('      </attenuation>')
    lines.append('      <direction>-0.5 0.1 -0.9</direction>')
    lines.append('    </light>')
    lines.append('')
    lines.append('    <model name="ground_plane">')
    lines.append('      <static>true</static>')
    lines.append('      <link name="link">')
    lines.append('        <collision name="collision">')
    lines.append('          <geometry>')
    lines.append('            <plane>')
    lines.append('              <normal>0 0 1</normal>')
    lines.append('              <size>100 100</size>')
    lines.append('            </plane>')
    lines.append('          </geometry>')
    lines.append('        </collision>')
    lines.append('        <visual name="visual">')
    lines.append('          <geometry>')
    lines.append('            <plane>')
    lines.append('              <normal>0 0 1</normal>')
    lines.append('              <size>100 100</size>')
    lines.append('            </plane>')
    lines.append('          </geometry>')
    lines.append('          <material>')
    lines.append('            <ambient>0.8 0.8 0.8 1</ambient>')
    lines.append('            <diffuse>0.8 0.8 0.8 1</diffuse>')
    lines.append('            <specular>0.8 0.8 0.8 1</specular>')
    lines.append('          </material>')
    lines.append('        </visual>')
    lines.append('      </link>')
    lines.append('    </model>')
    lines.append('')

    car_idx = 0
    for col_idx, x_center in enumerate(COLUMN_X):
        base_color = COLUMN_COLORS[col_idx]
        for y_pos in CAR_Y:
            color = vary_color(base_color, car_idx)
            name = f"car_{col_idx}_{car_idx % len(CAR_Y)}"
            pose = f"{x_center:.1f} {y_pos:.1f} 0 0 0 0"

            lines.append(f'    <model name="{name}">')
            lines.append(f'      <static>true</static>')
            lines.append(f'      <pose>{pose}</pose>')
            lines.append(f'      <link name="body">')
            lines.append(f'        <collision name="collision">')
            lines.append(f'          <geometry>')
            lines.append(f'            <box>')
            lines.append(f'              <size>{CAR_LENGTH} {CAR_WIDTH} {CAR_HEIGHT}</size>')
            lines.append(f'            </box>')
            lines.append(f'          </geometry>')
            lines.append(f'        </collision>')
            lines.append(f'        <visual name="visual">')
            lines.append(f'          <geometry>')
            lines.append(f'            <box>')
            lines.append(f'              <size>{CAR_LENGTH} {CAR_WIDTH} {CAR_HEIGHT}</size>')
            lines.append(f'            </box>')
            lines.append(f'          </geometry>')
            lines.append(f'          <material>')
            lines.append(f'            <ambient>{color[0]:.2f} {color[1]:.2f} {color[2]:.2f} 1</ambient>')
            lines.append(f'            <diffuse>{color[0]:.2f} {color[1]:.2f} {color[2]:.2f} 1</diffuse>')
            lines.append(f'          </material>')
            lines.append(f'        </visual>')
            lines.append(f'      </link>')
            lines.append(f'    </model>')

            car_idx += 1

    lines.append('')
    lines.append('  </world>')
    lines.append('</sdf>')

    with open(OUTPUT, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Generated {OUTPUT} with {car_idx} cars in {len(COLUMN_X)} columns.")


if __name__ == "__main__":
    generate_world()
