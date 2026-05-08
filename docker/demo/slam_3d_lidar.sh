#!/usr/bin/env bash

set -euo pipefail

ROBOT_NAMESPACE="${ROBOT_NAMESPACE:-panther}"
ROS_DISTRO="${ROS_DISTRO:-humble}"
LIDAR_TOPIC="${LIDAR_TOPIC:-/${ROBOT_NAMESPACE}/lidar_3d/ouster/points}"
BASE_FRAME="${BASE_FRAME:-${ROBOT_NAMESPACE}/base_link}"
ODOM_FRAME="${ODOM_FRAME:-${ROBOT_NAMESPACE}/odom}"
SLAM_ODOM_TOPIC="${SLAM_ODOM_TOPIC:-/slam/odometry}"
SLAM_DB_PATH="${SLAM_DB_PATH:-/autoware_data/slam/rtabmap.db}"

if [[ -f "/opt/ros/${ROS_DISTRO}/setup.bash" ]]; then
  set +u
  # shellcheck disable=SC1090
  source "/opt/ros/${ROS_DISTRO}/setup.bash"
  set -u
fi

if ! command -v ros2 >/dev/null 2>&1; then
  echo "ERROR: ros2 not found in PATH. PATH=${PATH}" >&2
  exit 1
fi

echo "Starting 3D LiDAR SLAM (RTAB-Map ICP)"
echo "  LIDAR_TOPIC=${LIDAR_TOPIC}"
echo "  BASE_FRAME=${BASE_FRAME}"
echo "  ODOM_FRAME=${ODOM_FRAME}"
echo "  SLAM_ODOM_TOPIC=${SLAM_ODOM_TOPIC}"
echo "  SLAM_DB_PATH=${SLAM_DB_PATH}"

mkdir -p "$(dirname "${SLAM_DB_PATH}")"

ros2 run rtabmap_odom icp_odometry --ros-args \
  -p use_sim_time:=true \
  -p frame_id:="${BASE_FRAME}" \
  -p odom_frame_id:="${ODOM_FRAME}" \
  -p publish_tf:=true \
  -p wait_imu_to_init:=false \
  -p deskewing:=false \
  -r scan_cloud:="${LIDAR_TOPIC}" \
  -r odom:="${SLAM_ODOM_TOPIC}" &
PID_ICP=$!

ros2 run rtabmap_slam rtabmap --ros-args \
  -p use_sim_time:=true \
  -p frame_id:="${BASE_FRAME}" \
  -p map_frame_id:=map \
  -p database_path:="${SLAM_DB_PATH}" \
  -p publish_tf:=true \
  -p subscribe_scan:=false \
  -p subscribe_scan_cloud:=true \
  -p subscribe_depth:=false \
  -p subscribe_rgb:=false \
  -p subscribe_odom_info:=false \
  -p Reg/Strategy:=1 \
  -p Icp/PointToPlane:=true \
  -p Icp/VoxelSize:=0.2 \
  -p Icp/CorrespondenceRatio:=0.2 \
  -p Grid/FromDepth:=false \
  -p Grid/RangeMax:=40.0 \
  -p Mem/IncrementalMemory:=true \
  -p Mem/InitWMWithAllNodes:=false \
  -r scan_cloud:="${LIDAR_TOPIC}" \
  -r odom:="${SLAM_ODOM_TOPIC}" &
PID_RTABMAP=$!

ros2 run topic_tools relay "${SLAM_ODOM_TOPIC}" /localization/kinematic_state &
PID_ODOM_RELAY=$!

cleanup() {
  kill "$PID_ICP" "$PID_RTABMAP" "$PID_ODOM_RELAY" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

wait
