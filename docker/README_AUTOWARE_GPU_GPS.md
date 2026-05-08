# GPS Simulation + Autoware (GPU)

This guide runs Husarion GPS simulation and Autoware in Docker with NVIDIA GPU.

## What this uses

- `demo/compose.simulation.gps.yaml` (Gazebo + GPS + RViz + GPS monitor)
- `demo/compose.perception.bridge.yaml` (topic relays to `/sensing/*`)
- `demo/compose.autoware.yaml` (Autoware container with `gpus: all`)

## Prerequisites

- NVIDIA driver installed on host
- NVIDIA Container Toolkit installed
- Docker Compose v2
- X11 available (`DISPLAY` set)

Quick checks:

```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.4.1-runtime-ubuntu22.04 nvidia-smi
```

## 1) Start full stack

From repository root:

```bash
cd docker/demo
xhost local:docker

# Use host NIC for CycloneDDS (example from this setup: wlo1)
export CYCLONE_IFACE=wlo1
export ROS_DOMAIN_ID=0

docker compose \
  -f compose.simulation.gps.yaml \
  -f compose.perception.bridge.yaml \
  -f compose.autoware.yaml \
  up -d
```

## 2) Verify bridge and GPU

```bash
docker exec -it autoware_topic_bridge bash -lc "source /opt/ros/humble/setup.bash && ros2 topic list | grep sensing"
docker exec -it autoware_universe nvidia-smi
```

Expected sensing topics:

- `/sensing/lidar/top/pointcloud_raw`
- `/sensing/camera/front/image_raw`
- `/sensing/camera/front/camera_info`
- `/sensing/camera/front/depth/image_raw`
- `/sensing/camera/front/depth/camera_info`

## 3) Enter Autoware container

```bash
docker exec -it autoware_universe bash
```

## 4) Run perception-only (no ML artifacts required)

Use clustering first for bring-up stability:

```bash
ros2 launch autoware_launch autoware.launch.xml \
  map_path:=/autoware_map \
  data_path:=/autoware_data/ml_models \
  vehicle_model:=sample_vehicle \
  sensor_model:=sample_sensor_kit \
  use_sim_time:=true \
  is_simulation:=true \
  launch_vehicle:=false \
  launch_system:=false \
  launch_map:=false \
  launch_localization:=false \
  launch_planning:=false \
  launch_control:=false \
  launch_api:=false \
  launch_sensing:=false \
  launch_sensing_driver:=false \
  launch_perception:=true \
  perception_mode:=lidar \
  lidar_detection_model:=clustering \
  input/pointcloud:=/sensing/lidar/top/pointcloud_raw \
  use_cuda_ground_segmentation:=false \
  cuda_pointcloud_preprocessing:=false \
  use_pointcloud_map:=false \
  use_vector_map:=false \
  use_traffic_light_recognition:=false
```

## 5) Optional: camera + lidar fusion with ML models

If you use `centerpoint` or camera-lidar ML fusion, download model artifacts into:

- host: `docker/demo/autoware_data/ml_models`
- container: `/autoware_data/ml_models`

If missing, launch fails with errors like:

`No such file or directory: '/autoware_data/ml_models/lidar_centerpoint/centerpoint_tiny_ml_package.param.yaml'`

## 6) Useful checks

```bash
# in autoware container
ros2 topic hz /sensing/lidar/top/pointcloud_raw
ros2 topic hz /sensing/camera/front/image_raw
ros2 topic list | grep -E "perception|object_recognition|detection|tracked"
```

## 7) Camera + LiDAR fusion launch helper

From `docker/demo`:

```bash
./run_autoware_camera_lidar_fusion.sh
```

This starts Autoware perception in `camera_lidar_fusion` mode with bridged topics:

- `/sensing/lidar/top/pointcloud_raw`
- `/sensing/camera/front/image_raw`
- `/sensing/camera/front/camera_info`

## Troubleshooting

- DDS binds `lo` only -> set `CYCLONE_IFACE` to real NIC (for example `wlo1`), recreate container.
- `cudaErrorInsufficientDriver` -> ensure container started with GPU (`gpus: all`) and `nvidia-smi` works inside `autoware_universe`.
- `autoware_launch` not found -> source `/opt/autoware/setup.bash`.
- ML file missing -> use clustering mode first or place artifacts in `autoware_data/ml_models`.

## Stop

```bash
docker compose \
  -f compose.simulation.gps.yaml \
  -f compose.perception.bridge.yaml \
  -f compose.autoware.yaml \
  down
```
