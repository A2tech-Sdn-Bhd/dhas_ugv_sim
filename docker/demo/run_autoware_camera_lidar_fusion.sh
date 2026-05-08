#!/usr/bin/env bash

set -euo pipefail

docker exec -it autoware_universe bash -lc '
set +u
source /opt/ros/humble/setup.bash
source /opt/autoware/setup.bash
set -u

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
  base_frame:=panther/base_link \
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
  use_pointcloud_map:=false \
  use_vector_map:=false \
  use_traffic_light_recognition:=false
'
