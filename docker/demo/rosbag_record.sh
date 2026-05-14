#!/usr/bin/env bash
# rosbag_record.sh  –  Record Panther topics required by lidarslam_ros2
#
# Called inside the rosbag_recorder Docker container.
# Env vars (all optional, have defaults):
#   ROBOT_NAMESPACE  – ROS namespace prefix   (default: panther)
#   BAG_OUTPUT_DIR   – host-mounted output dir (default: /rosbags)
#   BAG_PREFIX       – bag filename prefix     (default: panther_run)

set -eo pipefail

ROBOT_NAMESPACE="${ROBOT_NAMESPACE:-panther}"
BAG_OUTPUT_DIR="${BAG_OUTPUT_DIR:-/rosbags}"
BAG_PREFIX="${BAG_PREFIX:-panther_run}"
ROS_DISTRO="${ROS_DISTRO:-humble}"

# ── Source ROS ────────────────────────────────────────────────────────────────
if [[ -f "/opt/ros/${ROS_DISTRO}/setup.bash" ]]; then
    # shellcheck disable=SC1090
    set +u
    source "/opt/ros/${ROS_DISTRO}/setup.bash"
    set -u
fi

# ── Topics to record ─────────────────────────────────────────────────────────
# Core lidarslam_ros2 requirements:
#   - 3D LiDAR PointCloud2  (primary sensor for NDT SLAM)
#   - TF tree               (frame resolution during offline replay)
#   - /clock                (sim-time playback)
#
# Optional extras kept for post-processing / Autoware integration:
#   - Odometry              (used as initial guess, improves SLAM quality)
#   - IMU                   (optional motion prior)
#   - GPS fix               (can be fused via GPS factor if desired)
TOPICS=(
    /clock

    # ── Core: 3D LiDAR (lidarslam_ros2 input) ────────────────────────────────
    "/${ROBOT_NAMESPACE}/lidar_3d/ouster/points"

    # ── TF (required for frame resolution during bag replay) ──────────────────
    /tf
    /tf_static

    # ── Odometry (used as SLAM motion prior) ──────────────────────────────────
    "/${ROBOT_NAMESPACE}/odometry/filtered"
    "/${ROBOT_NAMESPACE}/odometry/wheels"

    # ── Optional extras ───────────────────────────────────────────────────────
    # Comment out topics below to reduce bag size if needed.
    "/${ROBOT_NAMESPACE}/imu/data"
    "/${ROBOT_NAMESPACE}/gps/fix"
    "/${ROBOT_NAMESPACE}/front_cam/color/image_raw"
    "/${ROBOT_NAMESPACE}/front_cam/color/camera_info"
    "/${ROBOT_NAMESPACE}/front_cam/depth/image_raw"
    "/${ROBOT_NAMESPACE}/front_cam/depth/camera_info"
)

# ── Output path ───────────────────────────────────────────────────────────────
mkdir -p "$BAG_OUTPUT_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BAG_PATH="${BAG_OUTPUT_DIR}/${BAG_PREFIX}_${TIMESTAMP}"

echo "================================================"
echo "  Panther Rosbag Recorder (lidarslam_ros2)"
echo "  Namespace : ${ROBOT_NAMESPACE}"
echo "  Output    : ${BAG_PATH}"
echo "  Topics    : ${#TOPICS[@]}"
echo "================================================"
printf '  %s\n' "${TOPICS[@]}"
echo ""

# ── Record ────────────────────────────────────────────────────────────────────
exec ros2 bag record \
    --storage mcap \
    --output "$BAG_PATH" \
    "${TOPICS[@]}"
