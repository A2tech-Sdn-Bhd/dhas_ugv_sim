#!/usr/bin/env bash

set -euo pipefail

ROBOT_NAMESPACE="${ROBOT_NAMESPACE:-panther}"
ROS_DISTRO="${ROS_DISTRO:-humble}"

if [[ -f "/opt/ros/${ROS_DISTRO}/setup.bash" ]]; then
  set +u
  # shellcheck disable=SC1090
  source "/opt/ros/${ROS_DISTRO}/setup.bash"
  set -u
fi

if [[ -f "/ros2_ws/install/setup.bash" ]]; then
  set +u
  # shellcheck disable=SC1091
  source "/ros2_ws/install/setup.bash"
  set -u
fi

if ! command -v ros2 >/dev/null 2>&1; then
  echo "ERROR: ros2 not found in PATH. PATH=${PATH}" >&2
  exit 1
fi

echo "Starting Autoware perception relays for namespace: ${ROBOT_NAMESPACE}"

python3 /bridge/lidar_point_type_adapter.py \
  --ros-args \
  -p input_topic:="/${ROBOT_NAMESPACE}/lidar_3d/ouster/points" \
  -p output_topic:="/sensing/lidar/top/pointcloud_raw" &
PID_LIDAR=$!

ros2 run topic_tools relay "/${ROBOT_NAMESPACE}/front_cam/color/image_raw" "/sensing/camera/front/image_raw" &
PID_RGB_IMAGE=$!

ros2 run topic_tools relay "/${ROBOT_NAMESPACE}/front_cam/color/camera_info" "/sensing/camera/front/camera_info" &
PID_RGB_INFO=$!

ros2 run topic_tools relay "/${ROBOT_NAMESPACE}/front_cam/depth/image_raw" "/sensing/camera/front/depth/image_raw" &
PID_DEPTH_IMAGE=$!

ros2 run topic_tools relay "/${ROBOT_NAMESPACE}/front_cam/depth/camera_info" "/sensing/camera/front/depth/camera_info" &
PID_DEPTH_INFO=$!

# TF alias for non-namespaced Autoware configs expecting `base_link`.
ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 \
  "${ROBOT_NAMESPACE}/base_link" "base_link" &
PID_BASE_LINK_ALIAS=$!

# Perception occupancy grid expects map frame in some launch profiles.
ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 \
  map "${ROBOT_NAMESPACE}/odom" &
PID_MAP_ALIAS=$!

cleanup() {
  kill "$PID_LIDAR" "$PID_RGB_IMAGE" "$PID_RGB_INFO" "$PID_DEPTH_IMAGE" "$PID_DEPTH_INFO" "$PID_BASE_LINK_ALIAS" "$PID_MAP_ALIAS" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

wait
