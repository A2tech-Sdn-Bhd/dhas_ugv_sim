# GPS Docker Quick Reference

## Quick Start

```bash
# Navigate to docker demo folder
cd docker/demo

# Run setup script (easiest)
chmod +x gps_setup.sh
./gps_setup.sh

# Or manually start
xhost local:docker
docker compose -f compose.simulation.gps.yaml up -d
```

## Monitor GPS Data

```bash
# GPS position
docker exec -it husarion_ugv_gazebo ros2 topic echo /gps/fix

# GPS-fused odometry
docker exec -it husarion_ugv_gazebo ros2 topic echo /odometry/filtered

# All ROS topics
docker exec -it husarion_ugv_gazebo ros2 topic list

# GPS logs
tail -f gps_logs/gps_status.log
```

## Container Management

```bash
# View status
docker compose -f compose.simulation.gps.yaml ps

# View logs
docker compose -f compose.simulation.gps.yaml logs -f

# Logs from specific service
docker compose -f compose.simulation.gps.yaml logs -f husarion_ugv_gazebo

# Stop all
docker compose -f compose.simulation.gps.yaml down

# Restart
docker compose -f compose.simulation.gps.yaml restart

# Shell access
docker exec -it husarion_ugv_gazebo bash
```

## Troubleshooting

```bash
# Check X11 forwarding
echo $DISPLAY

# Grant Docker X11 access
xhost local:docker

# Check GPS relay
docker exec -it husarion_ugv_gazebo ros2 topic list | grep gps

# View all topics with data
docker exec -it husarion_ugv_gazebo ros2 topic list -t

# Get topic info
docker exec -it husarion_ugv_gazebo ros2 topic info /gps/fix

# CPU/GPU usage
docker stats
```

## Environment Customization

```bash
# Set before running docker compose
export ROBOT_MODEL_NAME=panther  # or lynx
export ROBOT_NAMESPACE=robot1
export ROS_DOMAIN_ID=1

docker compose -f compose.simulation.gps.yaml up -d
```

## ROS Commands Inside Container

```bash
# List nodes
docker exec -it husarion_ugv_gazebo ros2 node list

# Inspect node
docker exec -it husarion_ugv_gazebo ros2 node info /gps_relay

# Service calls
docker exec -it husarion_ugv_gazebo ros2 service list

# Parameter list
docker exec -it husarion_ugv_gazebo ros2 param list

# Record rosbag
docker exec -it husarion_ugv_gazebo ros2 bag record /gps/fix /odometry/filtered
```

## Services Launched

| Service | Container | Purpose |
|---------|-----------|---------|
| Gazebo | husarion_ugv_gazebo | Simulation with GPS |
| RViz | husarion_rviz | 3D Visualization |
| Monitor | gps_monitor | GPS data logging |

## Log Locations

```bash
# Inside container
/ros2_ws/gps_logs/

# Local mount (host machine)
./gps_logs/

# Files
- gps_fix.log        # Raw GPS topic output
- odometry.log       # Filtered odometry output
- gps_status.log     # Timestamped GPS samples
```

## Files Created

- `compose.simulation.gps.yaml` - Docker Compose configuration with GPS
- `gps_setup.sh` - Automated setup script
- `.env.gps` - GPS-specific environment variables
- `GPS_DOCKER_GUIDE.md` - Detailed documentation
- `GPS_QUICK_REFERENCE.md` - This file

## See Also

- [GPS_DOCKER_GUIDE.md](./GPS_DOCKER_GUIDE.md) - Complete documentation
- [../README.md](../README.md) - Docker overview
- [../../README_GPS_SENSOR.md](../../README_GPS_SENSOR.md) - GPS configuration
