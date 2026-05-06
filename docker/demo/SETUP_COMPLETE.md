# ✅ Husarion UGV GPS Docker Setup - Complete!

## 🚀 Current Status

Your Husarion UGV simulation with GPS fusion is now **running successfully** in Docker with ROS2 Humble.

### Running Services
- ✅ **husarion_ugv_gazebo** - Gazebo simulation with GPS antenna
- ✅ **husarion_rviz** - 3D visualization
- ✅ **gps_monitor** - Logs GPS and odometry data

### Active Topics
- `/panther/gps/fix` - GPS position data (lat/lon/alt)
- `/panther/odometry/filtered` - GPS-fused odometry (wheels + IMU + GPS)
- `/panther/odometry/wheels` - Wheel encoder odometry
- `/panther/imu/data` - IMU measurements

## 📊 Verified Data

GPS Data Sample:
```
latitude: 50.08836736791197
longitude: 19.939128628805513
altitude: 0.32829941902309656
```

Filtered Odometry: **Active** - EKF is fusing GPS with wheel encoders and IMU

## 🔧 Configuration

### GPS Settings
- **Coordinate System**: ENU (East-North-Up)
- **Device Namespace**: gps
- **Parent Link**: cover_link
- **Position**: (0.0, 0.15, 0.0) relative to robot center
- **Fuse GPS**: True ✅
- **Localization Mode**: enu ✅

### Robot Details
- **Model**: panther
- **Namespace**: panther
- **Build Type**: simulation
- **ROS Version**: Humble

## 📋 Quick Commands

### Monitor GPS Data
```bash
# Real-time GPS fix
docker exec -it husarion_ugv_gazebo ros2 topic echo /panther/gps/fix

# Real-time filtered odometry (GPS-fused)
docker exec -it husarion_ugv_gazebo ros2 topic echo /panther/odometry/filtered

# List all topics
docker exec -it husarion_ugv_gazebo bash -c "source /opt/ros/humble/setup.bash && source /ros2_ws/install/setup.bash && ros2 topic list -t"
```

### Container Management
```bash
# View logs
docker compose -f compose.simulation.gps.yaml logs -f husarion_ugv_gazebo

# Shell access to container
docker exec -it husarion_ugv_gazebo bash

# Check container status
docker compose -f compose.simulation.gps.yaml ps

# Stop all containers
docker compose -f compose.simulation.gps.yaml down

# Restart
docker compose -f compose.simulation.gps.yaml up -d
```

### GPS Monitoring
```bash
# View GPS logs in real-time
tail -f gps_logs/gps_status.log

# View GPS fix log
tail -f gps_logs/gps_fix.log

# View odometry log
tail -f gps_logs/odometry.log
```

## 📁 Files Modified/Created

### New Files
- `compose.simulation.gps.yaml` - Docker Compose configuration with GPS
- `gps_setup.sh` - Automated setup script
- `.env.gps` - GPS environment variables
- `GPS_DOCKER_GUIDE.md` - Comprehensive documentation
- `GPS_QUICK_REFERENCE.md` - Quick reference card
- `gps_logs/` - Directory for GPS data logs

### Modified Files
- `husarion_ugv_description/config/components.yaml` - Added GPS antenna (ANT02) configuration
- `docker/README.md` - Added GPS Docker section

## 🔍 What's Happening

1. **Gazebo Simulation**: Simulates the Panther robot with a GPS antenna in a world environment
2. **GPS Antenna**: Publishes simulated GPS data on `/panther/gps/fix`
3. **EKF Filter**: Fuses GPS with wheel encoders and IMU for accurate localization
4. **RViz**: Visualizes the robot, sensor data, and coordinate frames
5. **GPS Monitor**: Continuously logs GPS and odometry data to files

## 📈 EKF Fusion Configuration

The Extended Kalman Filter (EKF) is configured to use:
- **Sensors**: Wheel encoders + IMU + GPS
- **Config**: `enu_localization_with_gps.yaml`
- **Output**: Fused odometry at `/panther/odometry/filtered`

The GPS data is converted to local XY coordinates using the `navsat_transform_node` before being fused.

## ✨ Next Steps

1. **Visualize in RViz**: The visualization should be running on your display
2. **Send Commands**: Move the robot and observe GPS tracking
3. **Analyze Data**: Check GPS logs for accuracy
4. **Customize**: Add more sensors or modify GPS location in components.yaml

Example command to move robot:
```bash
docker exec -it husarion_ugv_gazebo ros2 topic pub /panther/cmd_vel geometry_msgs/msg/Twist "linear: {x: 0.5}" -1
```

## 🐛 Troubleshooting

### GUI Not Showing
```bash
# Check X11 forwarding
echo $DISPLAY

# Grant access
xhost local:docker
```

### No GPS Data
```bash
# Verify GPS topic exists
docker exec -it husarion_ugv_gazebo bash -c "source /opt/ros/humble/setup.bash && source /ros2_ws/install/setup.bash && ros2 topic list -t | grep gps"

# Check container logs
docker compose -f compose.simulation.gps.yaml logs husarion_ugv_gazebo
```

### High CPU Usage
- Check if GPU acceleration is available
- Reduce Gazebo simulation frequency if needed

## 📚 Documentation

See also:
- [GPS_DOCKER_GUIDE.md](./GPS_DOCKER_GUIDE.md) - Detailed setup guide
- [GPS_QUICK_REFERENCE.md](./GPS_QUICK_REFERENCE.md) - Command reference
- [../../README_GPS_SENSOR.md](../../README_GPS_SENSOR.md) - GPS configuration details
- [../../README.md](../../README.md) - Project overview

---

**Setup Date**: 2026-05-06  
**Status**: ✅ Ready for GPS Testing  
**Last Updated**: Successfully tested GPS data flow and odometry fusion
