# GPS Testing with Docker - ROS2 Humble

This guide explains how to run the Husarion UGV simulation with GPS functionality in Docker containers using ROS2 Humble.

## Prerequisites

- Docker and Docker Compose installed
- X11 display server (for GUI visualization)
- At least 4GB of free RAM
- Optional: NVIDIA GPU with NVIDIA Container Toolkit (for better performance)

## Quick Start

### 1. Navigate to Docker Demo Directory
```bash
cd docker/demo
```

### 2. Run Setup Script (Recommended)
```bash
chmod +x gps_setup.sh
./gps_setup.sh
```

This script will:
- Verify Docker installation
- Configure X11 forwarding for GUI
- Create GPS logs directory
- Pull latest images
- Start all containers

### 3. Or Manual Setup

Allow Docker to access your display:
```bash
xhost local:docker
```

Start the containers with GPS enabled:
```bash
docker compose -f compose.simulation.gps.yaml up -d
```

## What Gets Launched

The `compose.simulation.gps.yaml` file launches three services:

### 1. **husarion_ugv_gazebo**
- Main simulation engine with Gazebo
- GPS data fusion enabled (`fuse_gps:=True`)
- ENU localization mode (`localization_mode:=enu`)
- Debug logging enabled

### 2. **rviz**
- 3D visualization of the robot and sensor data
- Displays robot pose and GPS information
- Depends on Gazebo service

### 3. **gps_monitor**
- Continuously logs GPS and odometry data
- Creates logs in `./gps_logs` directory
- Non-blocking service (doesn't affect other services)

## Monitoring GPS Data

### View GPS Fix Topic
```bash
docker exec -it husarion_ugv_gazebo ros2 topic echo /gps/fix
```

Expected output shows latitude, longitude, altitude from simulated GPS.

### View Filtered Odometry
```bash
docker exec -it husarion_ugv_gazebo ros2 topic echo /odometry/filtered
```

Shows fused position estimate from EKF with GPS data.

### View All ROS Topics
```bash
docker exec -it husarion_ugv_gazebo ros2 topic list
```

### Check GPS Status Logs
```bash
tail -f ./gps_logs/gps_status.log
```

View real-time GPS data samples being recorded.

## Container Management

### View Container Status
```bash
docker compose -f compose.simulation.gps.yaml ps
```

### View Container Logs
```bash
# All containers
docker compose -f compose.simulation.gps.yaml logs -f

# Specific container
docker compose -f compose.simulation.gps.yaml logs -f husarion_ugv_gazebo
```

### Stop Containers
```bash
docker compose -f compose.simulation.gps.yaml down
```

### Restart Containers
```bash
docker compose -f compose.simulation.gps.yaml restart
```

### Remove Containers and Volumes
```bash
docker compose -f compose.simulation.gps.yaml down -v
```

## GPU Acceleration (Optional)

If you have an NVIDIA GPU:

1. Install [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

2. Modify `compose.simulation.gps.yaml`:
   ```yaml
   <<:
     - *common-config
     - *gpu-config  # Change from *cpu-config to *gpu-config
   ```

3. Use `.env.gpu` instead of `.env.cpu` for better GPU support

## GPS Configuration Details

### Current Setup
- **Coordinate System**: ENU (East-North-Up)
- **GPS Fusion**: Enabled
- **Sensors Used**: Wheel encoders + IMU + GPS
- **Localization**: EKF (Extended Kalman Filter)

### Key Topics
| Topic | Type | Description |
|-------|------|-------------|
| `/gps/fix` | `sensor_msgs/NavSatFix` | GPS position data (lat/lon/alt) |
| `/gps_left/fix` | `sensor_msgs/NavSatFix` | Raw GPS from antenna |
| `/odometry/filtered` | `nav_msgs/Odometry` | Fused odometry estimate |
| `/imu/data` | `sensor_msgs/Imu` | IMU measurements |
| `/tf` | `tf2_msgs/TFMessage` | Coordinate frame transforms |

### Relay Mechanism
The setup includes a GPS relay that remaps:
- Source: `/gps_left/fix` (from GPS antenna)
- Target: `/gps/fix` (expected by EKF filter)

This ensures the EKF localization can read GPS data correctly.

## Troubleshooting

### X11 Display Issues
```bash
# If GUI doesn't appear, check X11 forwarding
echo $DISPLAY

# Grant Docker access to X11
xhost local:docker

# Or allow all
xhost local:
```

### GPU Not Being Used
Verify NVIDIA Container Toolkit is installed:
```bash
docker run --rm --gpus all nvidia/cuda:11.6.2-runtime-ubuntu22.04 nvidia-smi
```

### High CPU Usage
- Check if simulation is running: `docker compose ps`
- Reduce Gazebo simulation frequency (modify launch parameters)
- Use GPU acceleration if available

### No GPS Data
```bash
# Check if relay is working
docker exec -it husarion_ugv_gazebo ros2 topic list | grep gps

# Verify GPS sensor is spawned in Gazebo
docker exec -it husarion_ugv_gazebo ros2 topic echo /gps_left/fix
```

### Containers Keep Restarting
Check logs for errors:
```bash
docker compose -f compose.simulation.gps.yaml logs husarion_ugv_gazebo
```

## Environment Variables

You can customize behavior with environment variables:

```bash
# Change robot model
export ROBOT_MODEL_NAME=lynx

# Change namespace
export ROBOT_NAMESPACE=robot1

# Change ROS domain ID (for multiple robots)
export ROS_DOMAIN_ID=1

# Start containers
docker compose -f compose.simulation.gps.yaml up -d
```

## Advanced Configuration

### Modifying Launch Parameters
Edit `compose.simulation.gps.yaml` and modify the `command` section:

```yaml
command: >
  bash -c "
    ros2 launch husarion_ugv_gazebo simulation.launch.py
    fuse_gps:=True
    localization_mode:=enu
    log_level:=DEBUG
  "
```

Available parameters from README.md:
- `fuse_gps`: Enable/disable GPS fusion (True/False)
- `localization_mode`: Coordinate frame mode (relative/enu)
- `log_level`: Logging verbosity (DEBUG/INFO/WARN/ERROR)
- `robot_model`: Robot type (panther/lynx)

### Volume Mounting
Mount local directories for configuration:

```yaml
volumes:
  - /tmp/.X11-unix:/tmp/.X11-unix:rw
  - gps_logs:/ros2_ws/gps_logs
  - ./config:/ros2_ws/src/husarion_ugv_ros/config  # Custom configs
```

## Useful Docker Commands

```bash
# Execute ROS commands in running container
docker exec -it husarion_ugv_gazebo ros2 <command>

# Get container shell
docker exec -it husarion_ugv_gazebo bash

# View resource usage
docker stats

# Inspect container details
docker inspect husarion_ugv_gazebo

# Copy files from container
docker cp husarion_ugv_gazebo:/ros2_ws/gps_logs ./backup_logs
```

## Network Configuration

The setup uses `network_mode: host` which means:
- Containers share the host network
- Enables inter-container ROS communication
- All services see the same network interfaces
- Perfect for ROS multi-robot setup

## Next Steps

1. Verify GPS data is flowing: `ros2 topic echo /gps/fix`
2. Monitor localization accuracy: `ros2 topic echo /odometry/filtered`
3. Launch custom ROS nodes: `docker exec -it husarion_ugv_gazebo ros2 run <package> <executable>`
4. Create custom launch files based on your needs

## Documentation References

- [README_GPS_SENSOR.md](../../README_GPS_SENSOR.md) - GPS configuration guide
- [README.md](../../README.md) - Main project documentation
- [ROS_API.md](../../ROS_API.md) - ROS API reference
