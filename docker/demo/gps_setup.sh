#!/bin/bash
# GPS Testing Docker Setup Script
# This script prepares and runs Husarion UGV GPS simulation + Autoware in Docker

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

COMPOSE_ARGS=(
    -f compose.simulation.gps.yaml
    -f compose.perception.bridge.yaml
    -f compose.autoware.yaml
)

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Husarion UGV GPS Testing Setup${NC}"
echo -e "${GREEN}========================================${NC}\n"

# Check Docker and Docker Compose
echo -e "${YELLOW}Checking Docker installation...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker and Docker Compose found${NC}\n"

# Setup X11 forwarding
echo -e "${YELLOW}Setting up X11 display forwarding...${NC}"
DISPLAY=${DISPLAY:-:0}
export DISPLAY

if xhost local:docker 2>/dev/null; then
    echo -e "${GREEN}✓ X11 forwarding configured${NC}\n"
else
    echo -e "${YELLOW}⚠ Warning: Could not configure X11 forwarding${NC}"
    echo -e "${YELLOW}  GUI visualization may not work.${NC}"
    echo -e "${YELLOW}  You can still monitor GPS data via terminal commands.${NC}\n"
fi

# Create GPS logs directory
echo -e "${YELLOW}Creating GPS logs directory...${NC}"
mkdir -p ./gps_logs
echo -e "${GREEN}✓ GPS logs directory created at ./gps_logs${NC}\n"

# Create Autoware data directories
echo -e "${YELLOW}Creating Autoware directories...${NC}"
mkdir -p ./autoware_map ./autoware_data
echo -e "${GREEN}✓ Autoware directories ready (./autoware_map, ./autoware_data)${NC}\n"

# Select DDS network interface for Autoware
if [[ -z "${CYCLONE_IFACE:-}" ]]; then
    CYCLONE_IFACE=wlo1
fi

if [[ -n "${CYCLONE_IFACE:-}" ]]; then
    export CYCLONE_IFACE
    echo -e "${GREEN}✓ CYCLONE_IFACE=${CYCLONE_IFACE}${NC}\n"
else
    echo -e "${YELLOW}⚠ Warning: Could not auto-detect CYCLONE_IFACE. Using compose default.${NC}\n"
fi

# Cleanup old containers (if any)
echo -e "${YELLOW}Cleaning up old containers...${NC}"
docker compose "${COMPOSE_ARGS[@]}" down 2>/dev/null || true
echo -e "${GREEN}✓ Cleanup complete${NC}\n"

# Pull latest images (only non-build services)
echo -e "${YELLOW}Pulling latest Docker images...${NC}"
echo -e "${BLUE}(This may take a few minutes)${NC}"
if docker compose "${COMPOSE_ARGS[@]}" pull husarion_ugv_gazebo rviz gps_monitor autoware_topic_bridge; then
    echo -e "${GREEN}✓ Docker images updated${NC}\n"
else
    echo -e "${RED}✗ Failed to pull Docker images${NC}"
    exit 1
fi

# Build local Autoware image
echo -e "${YELLOW}Building local Autoware image...${NC}"
if docker compose "${COMPOSE_ARGS[@]}" build autoware; then
    echo -e "${GREEN}✓ Autoware image built${NC}\n"
else
    echo -e "${RED}✗ Failed to build Autoware image${NC}"
    exit 1
fi

# Start containers
echo -e "${YELLOW}Starting containers...${NC}"
if docker compose "${COMPOSE_ARGS[@]}" up -d; then
    echo -e "${GREEN}✓ Containers started${NC}\n"
else
    echo -e "${RED}✗ Failed to start containers${NC}"
    exit 1
fi

# Wait for containers to be ready
echo -e "${YELLOW}Waiting for services to initialize (40 seconds)...${NC}"
echo -e "${BLUE}|"
for i in {40..1}; do
    echo -ne "\r${BLUE}Remaining: $i seconds...${NC}    "
    sleep 1
done
echo -e "\r${GREEN}✓ Initialization complete${NC}\n"

# Check container status
echo -e "${YELLOW}Checking container status...${NC}"
docker compose "${COMPOSE_ARGS[@]}" ps

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${YELLOW}Quick Commands:${NC}"
echo -e "${BLUE}View GPS fix data:${NC}"
echo "  docker exec -it husarion_ugv_gazebo ros2 topic echo /gps/fix"
echo ""
echo -e "${BLUE}View filtered odometry:${NC}"
echo "  docker exec -it husarion_ugv_gazebo ros2 topic echo /odometry/filtered"
echo ""
echo -e "${BLUE}View GPS logs:${NC}"
echo "  tail -f ./gps_logs/gps_status.log"
echo ""
echo -e "${BLUE}Stop containers:${NC}"
echo "  docker compose ${COMPOSE_ARGS[*]} down"
echo ""
echo -e "${BLUE}View all ROS topics:${NC}"
echo "  docker exec -it husarion_ugv_gazebo ros2 topic list"
echo ""
echo -e "${BLUE}View simulation logs:${NC}"
echo "  docker compose ${COMPOSE_ARGS[*]} logs -f husarion_ugv_gazebo"
echo ""
echo -e "${BLUE}View Autoware logs:${NC}"
echo "  docker compose ${COMPOSE_ARGS[*]} logs -f autoware"
echo ""
echo -e "${BLUE}Get Autoware shell:${NC}"
echo "  docker exec -it autoware_universe bash"
echo ""
echo -e "${BLUE}Get simulation shell:${NC}"
echo "  docker exec -it husarion_ugv_gazebo bash"
echo ""
echo -e "${YELLOW}For detailed documentation, see GPS_DOCKER_GUIDE.md and ../README_AUTOWARE_GPU_GPS.md${NC}\n"
