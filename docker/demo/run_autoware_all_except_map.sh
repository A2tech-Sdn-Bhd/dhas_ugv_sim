#!/usr/bin/env bash

set -euo pipefail

docker exec -it autoware_universe bash -lc '
set +u
source /opt/ros/humble/setup.bash
source /opt/autoware/setup.bash
set -u

PYTHONDONTWRITEBYTECODE=1 python3 /dhas_ugv_sim/docker/demo/panther_autoware_vehicle_bridge.py \
  --ros-args \
  -p odom_topic:=/panther/odometry/wheels \
  -p gps_fix_topic:=/panther/gps/fix \
  -p base_frame:=base_link \
  -p gnss_frame:=gnss_base_link &
VEHICLE_BRIDGE_PID=$!

ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 \
  base_link gnss_base_link &
GNSS_TF_PID=$!

trap "kill ${VEHICLE_BRIDGE_PID} ${GNSS_TF_PID} 2>/dev/null || true" EXIT INT TERM

ros2 launch autoware_launch autoware.launch.xml \
  map_path:=/autoware_map \
  data_path:=/autoware_data/ml_models \
  vehicle_model:=sample_vehicle \
  sensor_model:=sample_sensor_kit \
  use_sim_time:=true \
  is_simulation:=true \
  launch_vehicle:=true \
  launch_system:=true \
  launch_map:=true \
  launch_localization:=true \
  launch_planning:=true \
  launch_control:=true \
  launch_api:=true \
  launch_sensing:=true \
  launch_sensing_driver:=false \
  launch_perception:=true \
  base_frame:=panther/base_link \
  input_pointcloud:=/sensing/lidar/top/pointcloud_raw \
  input_imu_topic:=/panther/imu/data \
  perception_mode:=camera_lidar_fusion \
  lidar_detection_model:=clustering \
  input/pointcloud:=/sensing/lidar/top/pointcloud_raw \
  image_number:=1 \
  image_raw0:=/sensing/camera/front/image_raw \
  camera_info0:=/sensing/camera/front/camera_info \
  segmentation_pointcloud_fusion_camera_ids:="[0]" \
  camera_vru_detector_rois_ids:="[0]" \
  use_irregular_object_detector:=false \
  use_image_segmentation_based_filter:=false \
  use_cuda_ground_segmentation:=false \
  cuda_pointcloud_preprocessing:=false \
  use_pointcloud_map:=true \
  use_vector_map:=true \
  pointcloud_map_file:=map.pcd \
  lanelet2_map_file:=lanelet2_map_local_aligned.osm \
  use_traffic_light_recognition:=false
'
