#!/bin/bash
# lidarslam_ros2 – Rosbag Recorder & Autoware PCD Map Generation
#
# Builds a 3D PCD map (pointcloud_map.pcd) compatible with Autoware Universe
# using lidarslam_ros2 (NDT-based 3D LiDAR SLAM, native ROS 2 Humble).
#
# Autoware map output layout (./maps/):
#   pointcloud_map.pcd       – 3D point-cloud map for NDT localisation
#   map_projector_info.yaml  – coordinate-system declaration required by Autoware
#
# Workflow
# ─────────
#  1. Build image   : ./liosam_setup.sh build
#  2. Record bag    : ./liosam_setup.sh record        (while sim is running)
#     Stop recorder : docker stop rosbag_recorder
#  3a. Live SLAM    : ./liosam_setup.sh slam           (runs alongside sim)
#      Save map     : ./liosam_setup.sh save_map
#  3b. Offline map  : ./liosam_setup.sh map [bag_dir]  (from a recorded bag)
#  4. Stop all      : ./liosam_setup.sh down

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

COMPOSE_FILE="compose.liosam.yaml"
IMAGE_NAME="local/lidarslam:humble"

# ── Colour codes ──────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

banner() {
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  Panther lidarslam_ros2 – Autoware PCD Map    ${NC}"
    echo -e "${GREEN}================================================${NC}\n"
}

usage() {
    echo -e "${CYAN}Usage:${NC}"
    echo "  $0 build               – Build the lidarslam Docker image"
    echo "  $0 record              – Start rosbag recorder (while sim runs)"
    echo "  $0 slam                – Start live SLAM alongside simulation"
    echo "  $0 save_map            – Save PCD map from running SLAM instance"
    echo "  $0 map [bag_dir]       – Offline: replay bag and generate PCD map"
    echo "  $0 down                – Stop and remove all SLAM containers"
    echo ""
    echo -e "${YELLOW}Output (Autoware-ready map):${NC}"
    echo "  ./maps/pointcloud_map.pcd"
    echo "  ./maps/map_projector_info.yaml"
    echo ""
    echo -e "${YELLOW}Environment variables:${NC}"
    echo "  ROS_DOMAIN_ID    (default: 0)"
    echo "  ROBOT_NAMESPACE  (default: panther)"
    echo "  BAG_PREFIX       (default: panther_run)"
    echo "  BAG_FILE         bag path for offline mode (used with 'map')"
    echo "  USE_SIM_TIME     (default: true)"
    echo ""
}

check_deps() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}✗ Docker is not installed.${NC}"; exit 1
    fi
    if ! docker compose version &> /dev/null 2>&1; then
        echo -e "${RED}✗ Docker Compose (v2) is not installed.${NC}"; exit 1
    fi
}

setup_dirs() {
    echo -e "${YELLOW}Creating output directories...${NC}"
    mkdir -p ./rosbags ./maps
    echo -e "${GREEN}✓ ./rosbags – recorded bags${NC}"
    echo -e "${GREEN}✓ ./maps    – Autoware PCD map output${NC}\n"
}

setup_display() {
    DISPLAY=${DISPLAY:-:0}
    export DISPLAY
    if xhost local:docker 2>/dev/null; then
        echo -e "${GREEN}✓ X11 forwarding configured${NC}\n"
    else
        echo -e "${YELLOW}⚠ X11 not available – running headless${NC}\n"
    fi
}

# Write the map_projector_info.yaml Autoware requires alongside the PCD
write_map_projector_info() {
    local map_dir="${1:-./maps}"
    cat > "${map_dir}/map_projector_info.yaml" <<'EOF'
# Autoware map_projector_info.yaml
# projector_type options:
#   Local  – no real-world geo-reference (simulation / indoor)
#   MGRS   – military grid reference (outdoor, real robot)
#   UTM    – universal transverse mercator
projector_type: Local
EOF
    echo -e "${GREEN}✓ ${map_dir}/map_projector_info.yaml written${NC}"
}

build_image() {
    echo -e "${YELLOW}Building lidarslam_ros2 Docker image (${IMAGE_NAME})...${NC}"
    echo -e "${BLUE}Note: first build compiles lidarslam_ros2 from source (~5-10 min)${NC}"
    docker compose -f "$COMPOSE_FILE" build lidarslam
    echo -e "${GREEN}✓ Image built: ${IMAGE_NAME}${NC}\n"
}

ensure_image() {
    if ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
        build_image
    fi
}

cmd_build() {
    banner; check_deps; build_image
}

cmd_record() {
    banner; check_deps; setup_dirs
    ensure_image

    echo -e "${YELLOW}Starting rosbag recorder...${NC}"
    echo -e "${BLUE}Topics recorded:${NC}"
    echo "  /clock"
    echo "  /panther/lidar_3d/ouster/points   ← primary SLAM input"
    echo "  /panther/odometry/filtered"
    echo "  /panther/odometry/wheels"
    echo "  /panther/imu/data"
    echo "  /panther/gps/fix"
    echo "  /tf  /tf_static"
    echo ""

    docker compose -f "$COMPOSE_FILE" up -d rosbag_recorder
    echo -e "${GREEN}✓ Recorder started (container: rosbag_recorder)${NC}\n"
    echo -e "${YELLOW}Commands:${NC}"
    echo "  Follow logs : docker logs -f rosbag_recorder"
    echo "  Stop        : docker stop rosbag_recorder"
    echo "  List bags   : ls -lh ./rosbags/"
    echo ""
}

cmd_slam() {
    banner; check_deps; setup_dirs; setup_display
    ensure_image

    echo -e "${YELLOW}Starting live lidarslam_ros2...${NC}"
    docker compose -f "$COMPOSE_FILE" up -d lidarslam
    echo -e "${GREEN}✓ lidarslam started (container: lidarslam)${NC}\n"

    echo -e "${YELLOW}Commands:${NC}"
    echo "  Follow logs : docker logs -f lidarslam"
    echo "  Save map    : $0 save_map"
    echo "  Stop        : docker compose -f $COMPOSE_FILE down lidarslam"
    echo ""
}

cmd_save_map() {
    banner
    echo -e "${YELLOW}Calling /map_save service on running lidarslam container...${NC}"
    docker exec lidarslam bash -lc "
        source /opt/ros/humble/setup.bash &&
        source /slam_ws/install/setup.bash &&
        ros2 service call /map_save std_srvs/srv/Empty {}
    "
    write_map_projector_info ./maps
    echo ""
    echo -e "${GREEN}✓ PCD map saved. Autoware-ready files:${NC}"
    ls -lh ./maps/ 2>/dev/null || true
    echo ""
    echo -e "${YELLOW}Copy to your Autoware map directory:${NC}"
    echo "  cp ./maps/pointcloud_map.pcd    <autoware_map_dir>/"
    echo "  cp ./maps/map_projector_info.yaml <autoware_map_dir>/"
}

cmd_map() {
    banner; check_deps; setup_dirs
    ensure_image

    local bag_file="${1:-}"
    if [[ -z "$bag_file" ]]; then
        bag_file=$(ls -td ./rosbags/*/ 2>/dev/null | head -n 1 || true)
        if [[ -z "$bag_file" ]]; then
            echo -e "${RED}✗ No bag found in ./rosbags/. Pass path explicitly:${NC}"
            echo "    $0 map ./rosbags/panther_run_20260512_120000"
            exit 1
        fi
        echo -e "${BLUE}Auto-detected bag: ${bag_file}${NC}"
    fi

    bag_file="$(realpath "$bag_file")"
    if [[ ! -e "$bag_file" ]]; then
        echo -e "${RED}✗ Bag not found: ${bag_file}${NC}"; exit 1
    fi

    echo -e "${YELLOW}Running offline lidarslam_ros2 map generation...${NC}"
    echo -e "${BLUE}  Bag : ${bag_file}${NC}"
    echo -e "${BLUE}  Out : ./maps/${NC}\n"

    BAG_FILE="$bag_file" docker compose \
        -f "$COMPOSE_FILE" \
        --profile offline \
        run --rm \
        -e BAG_FILE="$bag_file" \
        -v "${bag_file}:${bag_file}:ro" \
        lidarslam_offline

    write_map_projector_info ./maps

    echo ""
    echo -e "${GREEN}✓ Autoware-ready map files:${NC}"
    ls -lh ./maps/ 2>/dev/null || true
    echo ""
    echo -e "${YELLOW}Copy to your Autoware map directory:${NC}"
    echo "  cp ./maps/pointcloud_map.pcd     <autoware_map_dir>/"
    echo "  cp ./maps/map_projector_info.yaml <autoware_map_dir>/"
}

cmd_down() {
    echo -e "${YELLOW}Stopping lidarslam containers...${NC}"
    docker compose -f "$COMPOSE_FILE" --profile offline down 2>/dev/null || true
    echo -e "${GREEN}✓ Containers stopped${NC}"
}

# ── Main ──────────────────────────────────────────────────────────────────────
case "${1:-help}" in
    build)    cmd_build ;;
    record)   cmd_record ;;
    slam)     cmd_slam ;;
    save_map) cmd_save_map ;;
    map)      cmd_map "${2:-}" ;;
    down)     cmd_down ;;
    *)        banner; usage ;;
esac
