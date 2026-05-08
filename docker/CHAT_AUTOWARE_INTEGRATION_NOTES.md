# Husarion GPS + Autoware Integration Notes

This document summarizes setup, fixes, and run commands from this session.

## Final stack

Use these compose files together:

- `docker/demo/compose.simulation.gps.yaml`
- `docker/demo/compose.perception.bridge.yaml`
- `docker/demo/compose.autoware.yaml`

Main helper scripts:

- `docker/demo/gps_setup.sh`
- `docker/demo/perception_bridge.sh`
- `docker/demo/run_autoware_camera_lidar_fusion.sh`

## What was fixed

### 1) Autoware container startup/env

- Added local image build for Autoware in `docker/demo/compose.autoware.yaml`.
- Added ROS/Autoware auto-source in shell profile via `docker/demo/Dockerfile.autoware`.
- Added GPU runtime in compose (`gpus: all`, `.env.gpu`).

### 2) DDS interface issues

- Added `CYCLONEDDS_URI` with NIC selection (`CYCLONE_IFACE`) in compose.
- `gps_setup.sh` auto-detects interface and exports `CYCLONE_IFACE`.

### 3) Perception topic bridge

- Added bridge compose `docker/demo/compose.perception.bridge.yaml`.
- Added adapter `docker/demo/lidar_point_type_adapter.py` to convert LiDAR cloud to Autoware `PointXYZIRC` layout.
- Added TF aliases in `docker/demo/perception_bridge.sh`:
  - `panther/base_link -> base_link`
  - `map -> panther/odom`

### 4) World file compatibility

- `worlds/parking_lot_world.sdf` updated with required GZ sim plugins and spherical coordinates.
- All Prius includes set to `<static>true</static>` to avoid heavy dynamic physics and blocked motion.

## Bring-up commands

From `docker/demo`:

```bash
xhost local:docker
export CYCLONE_IFACE=enp5s0
export GZ_WORLD=/ros2_ws/worlds/parking_lot_world.sdf

docker compose \
  -f compose.simulation.gps.yaml \
  -f compose.perception.bridge.yaml \
  -f compose.autoware.yaml \
  up -d
```

Or use helper:

```bash
cd docker/demo
./gps_setup.sh
```

## Camera + LiDAR fusion run

Run (stable mode):

```bash
cd docker/demo
./run_autoware_camera_lidar_fusion.sh
```

Current script uses:

- `perception_mode:=camera_lidar_fusion`
- `lidar_detection_model:=clustering`
- `use_irregular_object_detector:=false`
- `use_image_segmentation_based_filter:=false`

Reason: avoids heavy/unstable pointpainting/centerpoint crashes on low VRAM setups.

## How to get ML models (important)

ML artifacts are needed for models like `centerpoint`, `pointpainting`, traffic-light/camera ML detectors.

### Official method (recommended)

On host:

```bash
cd ~
git clone https://github.com/autowarefoundation/autoware.git
cd autoware

bash ansible/scripts/install-ansible.sh
ansible-galaxy collection install -f -r ansible-galaxy-requirements.yaml
ansible-playbook autoware.dev_env.download_artifacts -e "data_dir=$HOME/autoware_data" --ask-become-pass
```

Copy artifacts into this project mount path:

```bash
mkdir -p /home/a2tech/Desktop/project/a2tech/dhas_ugv_sim/docker/demo/autoware_data/ml_models
rsync -a ~/autoware_data/ /home/a2tech/Desktop/project/a2tech/dhas_ugv_sim/docker/demo/autoware_data/ml_models/
```

Example required file check:

```bash
ls /home/a2tech/Desktop/project/a2tech/dhas_ugv_sim/docker/demo/autoware_data/ml_models/lidar_centerpoint/centerpoint_tiny_ml_package.param.yaml
```

Inside container, mounted path is:

- `/autoware_data/ml_models`

## Verification commands

```bash
# Sim topics
docker exec -it husarion_ugv_gazebo bash -lc "source /opt/ros/humble/setup.bash && ros2 topic list"

# Bridged sensing topics
docker exec -it autoware_topic_bridge bash -lc "source /opt/ros/humble/setup.bash && ros2 topic list | grep sensing"

# Perception outputs
docker exec -it autoware_universe bash -lc "source /opt/ros/humble/setup.bash && source /opt/autoware/setup.bash && ros2 topic list | grep object_recognition"
```

## Frequent issues and meaning

- `The pointcloud layout is not compatible with PointXYZIRC`:
  bridge/adaptation problem. Fixed by `lidar_point_type_adapter.py`.

- `frame [map] does not exist` in RViz:
  map/localization disabled. Use fixed frame `base_link` / `panther/odom`, or enable map stack.

- `No vector map received`:
  object lanelet filter needs lanelet map. Disable vector map or provide lanelet2 map.

- TensorRT `building engine...` long startup:
  normal first run. Engine cache makes next run faster.

- RViz GL errors (`iris`, `dri3`):
  rendering warning; can still run headless or with reduced visualization.

## Related docs

- `docker/README_AUTOWARE_GPU_GPS.md`
- `docker/demo/PERCEPTION_BRIDGE.md`
- `docker/demo/GPS_DOCKER_GUIDE.md`
