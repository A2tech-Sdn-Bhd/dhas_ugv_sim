# Husarion UGV ROS Setup Instructions

## Installation Steps

After running the following commands:

```bash
vcs import src < src/husarion_ugv_ros/husarion_ugv/${HUSARION_ROS_BUILD_TYPE}_deps.repos
sudo rosdep init
rosdep update --rosdistro $ROS_DISTRO
rosdep install --from-paths src -y -i
```

## Required Manual Modifications

### GPS Sensor Configuration

You need to modify the GPS sensor configuration in the `husarion_components_description` package.

**File Location:**
```
husarion_components_description/urdf/teltonika_003R-00253.urdf.xacro
```

**Changes Required:**

#### Line 29 - Joint Name
Change from:
```xml
<joint name="${parent_link.rstrip('_link')}_to_antenna_joint"
```

To:
```xml
<joint name="${parent_link.rstrip('_link')}_to_${device_namespace}_antenna_joint"
```

#### Line 72 - Sensor Name
Change from:
```xml
<sensor name="navsat" type="navsat">
```

To:
```xml
<sensor name="${device_namespace}_navsat" type="navsat">
```

---

**Note:** These modifications ensure proper namespacing for the GPS sensor components, allowing for multiple GPS sensors or proper device identification in your robot configuration.

### GPS Topic Remapping

The localization system expects GPS data on the topic `/gps/fix`, but the GPS antenna publishes to `/gps_left/fix` (based on `device_namespace`).

**Why remapping is needed:**
- GPS antenna publishes: `/gps_left/fix` (from `device_namespace: gps_left`)
- EKF localization reads: `/gps/fix` (hardcoded in config)
- Solution: Use a relay node to remap the topic

**The remapping is already configured in `simulate_robot.launch.py`:**
```python
# GPS relay: remap /gps_left/fix to /gps/fix for localization
gps_relay = Node(
    package="topic_tools",
    executable="relay",
    name="gps_relay",
    arguments=["gps_left/fix", "gps/fix"],
    namespace=namespace,
)
```

**If you use a different GPS device_namespace**, update the relay arguments accordingly.

## Simulation Setup

### Launch Simulation with Robot

Run these commands in separate terminals:

```bash
# Terminal 1: Launch Gazebo simulator
ros2 launch husarion_gz_worlds gz_sim.launch.py

# Terminal 2: Spawn robot with GPS-enabled localization
ros2 launch husarion_ugv_gazebo simulate_robot.launch.py fuse_gps:=True localization_mode:=enu

# Terminal 3: Launch RViz for visualization
ros2 launch husarion_ugv_description rviz.launch.py
```

### Key Packages

- **`husarion_ugv_controller`** - Handles Gazebo and ROS 2 bridging
- **`husarion_ugv_description`** - Contains robot URDF files
- **`husarion_ugv_gazebo`** - Gazebo simulation package
- **`husarion_ugv_localization`** - Localization package with EKF sensor fusion

**Documentation:**
- Package overview: https://husarion.com/manuals/panther/software/ros2/packages-overview/
- ROS 2 API: https://husarion.com/manuals/panther/ros2-api/

### Localization Options

You can customize the localization configuration when launching the robot:

**1. Relative Localization (default)**
```bash
ros2 launch husarion_ugv_gazebo simulate_robot.launch.py localization_mode:=relative
```
- Odometry relative to initial position with zero orientation
- Sensors: Wheel encoders + IMU
- Config: `relative_localization.yaml`

**2. ENU Localization**
```bash
ros2 launch husarion_ugv_gazebo simulate_robot.launch.py localization_mode:=enu
```
- East-North-Up coordinate system (prepares for GPS use, but doesn't use it yet)
- Sensors: Wheel encoders + IMU (NO GPS)
- Config: `enu_localization.yaml`
- **Note:** ENU mode aligns orientation to compass directions, but still doesn't fuse GPS data

**3. Relative Localization with GPS**
```bash
ros2 launch husarion_ugv_gazebo simulate_robot.launch.py localization_mode:=relative fuse_gps:=True
```
- Relative mode with GPS data fusion
- Sensors: Wheel encoders + IMU + GPS
- Config: `relative_localization_with_gps.yaml`

**4. ENU Localization with GPS**
```bash
ros2 launch husarion_ugv_gazebo simulate_robot.launch.py localization_mode:=enu fuse_gps:=True
```
- ENU coordinate system with GPS data fusion
- Sensors: Wheel encoders + IMU + GPS
- Config: `enu_localization_with_gps.yaml`

**5. Disable EKF (raw odometry only)**
```bash
ros2 launch husarion_ugv_gazebo simulate_robot.launch.py use_ekf:=False
```
- No sensor fusion, raw odometry from wheel encoders

### Using GPS Fusion

To enable GPS fusion in your localization setup, you need:

**1. Add GPS antenna to `components.yaml`**

Edit `src/husarion_ugv_ros/husarion_ugv_description/config/components.yaml`:

```yaml
components:
  - type: ANT02
    parent_link: cover_link
    xyz: 0.0 0.15 0.0
    rpy: 0.0 0.0 0.0
    device_namespace: gps_left
```

**2. Rebuild the robot description**
```bash
cd /home/sqlee/husarion00_ws
colcon build --packages-select husarion_ugv_description
source install/setup.bash
```

**3. Launch with GPS fusion enabled**
```bash
# Terminal 1: Launch Gazebo
ros2 launch husarion_gz_worlds gz_sim.launch.py

# Terminal 2: Launch robot with GPS fusion
ros2 launch husarion_ugv_gazebo simulate_robot.launch.py fuse_gps:=True localization_mode:=enu

# Terminal 3: Launch RViz
ros2 launch husarion_ugv_description rviz.launch.py
```

**4. Verify GPS data**
```bash
# Check GPS fix topic
ros2 topic echo /gps/fix

# Check filtered odometry with GPS
ros2 topic echo /odometry/filtered
```

**How GPS Fusion Works:**
- The GPS antenna publishes data on `/gps_left/fix` (or based on `device_namespace` in components.yaml)
- **A relay node remaps `/gps_left/fix` to `/gps/fix`** because the EKF localization reads from `/gps/fix`
  - This remapping is done by `gps_relay` node (see simulate_robot.launch.py:258-265)
  - Uses `topic_tools` relay: `arguments=["gps_left/fix", "gps/fix"]`
- The EKF (`ekf_filter_node`) reads `/gps/fix` and fuses it with wheel encoders and IMU
- `navsat_transform_node` converts GPS lat/lon to local XY coordinates
- Fused odometry is published on `/odometry/filtered`

**Important:** If you use a different `device_namespace` for your GPS antenna (e.g., `my_gps`), you need to update the relay arguments from `gps_left/fix` to `my_gps/fix`.

### Understanding `localization_mode` vs `fuse_gps`

These are **two separate parameters** that control different aspects:

**`localization_mode`** - Controls coordinate frame orientation:
- `relative`: Robot's initial orientation becomes 0° (arbitrary)
- `enu`: Orientation follows compass (East=0°, North=90°)

**`fuse_gps`** - Controls whether GPS data is used:
- `False`: Don't use GPS sensor data (default)
- `True`: Fuse GPS position into localization

**Important:** ENU mode does NOT automatically use GPS. It only prepares the coordinate frame to align with compass directions, which is useful for GPS but doesn't require it.

### Comparison: ENU vs ENU with GPS

**Command 1: ENU without GPS**
```bash
ros2 launch husarion_ugv_gazebo simulate_robot.launch.py localization_mode:=enu
```
- Uses ENU coordinate frame (aligned to compass)
- Still only uses wheel encoders + IMU
- No GPS data fusion
- Suitable for indoor navigation in compass-aligned buildings

**Command 2: ENU with GPS**
```bash
ros2 launch husarion_ugv_gazebo simulate_robot.launch.py localization_mode:=enu fuse_gps:=True
```
- Uses ENU coordinate frame (aligned to compass)
- Fuses GPS position data with wheel encoders + IMU
- GPS corrects position drift
- Suitable for outdoor navigation with absolute positioning


## Adding Components

Components (sensors, manipulators) are configured in `components.yaml`:

```
src/husarion_ugv_ros/husarion_ugv_description/config/components.yaml
```

### Available Components

| Code  | Device Name                  | Type        |
|-------|------------------------------|-------------|
| ANT02 | Teltonika 003R-00253         | GPS Antenna |
| CAM01 | Orbbec Astra                 | RGB-D Camera|
| CAM03 | StereoLabs ZED 2             | Stereo Camera|
| CAM04 | StereoLabs ZED 2i            | Stereo Camera|
| CAM06 | StereoLabs ZED X             | Stereo Camera|
| CAM11 | Luxonis OAK-D-PRO            | RGB-D Camera|
| LDR01 | RPLIDAR S1                   | 2D LiDAR    |
| LDR06 | RPLIDAR S3                   | 2D LiDAR    |
| LDR10 | Ouster OS0-32                | 3D LiDAR    |
| LDR11 | Ouster OS0-64                | 3D LiDAR    |
| LDR12 | Ouster OS0-128               | 3D LiDAR    |
| LDR13 | Ouster OS1-32                | 3D LiDAR    |
| LDR14 | Ouster OS1-64                | 3D LiDAR    |
| LDR15 | Ouster OS1-128               | 3D LiDAR    |
| LDR20 | Velodyne Puck                | 3D LiDAR    |
| MAN01 | Universal Robots UR3e        | Manipulator |
| MAN02 | Universal Robots UR5e        | Manipulator |
| MAN04 | 6DoF Kinova Gen3             | Manipulator |
| MAN05 | 6DoF Kinova Gen3 + 3D vision | Manipulator |
| MAN06 | 7DoF Kinova Gen3             | Manipulator |
| MAN07 | 7DoF Kinova Gen3 + 3D vision | Manipulator |
| GRP02 | Robotiq 2F-85                | Gripper     |
| WCH01 | Wibotic receiver             | Wireless Charger |
| DEV02 | Developer Kit                | Dev Mount   |

### Component Configuration Examples

Edit `components.yaml` to add sensors:

**Example 1: Add GPS Antennas**
```yaml
components:
  - type: ANT02
    parent_link: cover_link
    xyz: 0.0 0.15 0.0
    rpy: 0.0 0.0 0.0
    device_namespace: gps_left

  - type: ANT02
    parent_link: cover_link
    xyz: 0.0 -0.15 0.0
    rpy: 0.0 0.0 0.0
    device_namespace: gps_right
```

**Example 2: Add 2D LiDAR**
```yaml
components:
  - type: LDR06
    parent_link: mount_link
    xyz: 0.0 0.0 0.1
    rpy: 0.0 0.0 0.0
    device_namespace: lidar
```

**Example 3: Add 3D LiDAR and Camera**
```yaml
components:
  - type: LDR13
    parent_link: mount_link
    xyz: 0.0 0.0 0.15
    rpy: 0.0 0.0 0.0
    device_namespace: lidar_3d

  - type: CAM01
    parent_link: mount_link
    xyz: 0.15 0.0 0.05
    rpy: 0.0 0.0 0.0
    device_namespace: front_camera
```

**After editing, rebuild:**
```bash
cd /home/sqlee/husarion00_ws
colcon build --packages-select husarion_ugv_description
source install/setup.bash
```

### Custom Component Development

If you want to edit existing components or add custom components, you can modify the URDF files in the `husarion_components_description` package:

**Package Location:**
```
src/husarion_components_description/urdf/
```

**Available component URDF files:**
- `slamtec_rplidar.urdf.xacro` - 2D LiDAR sensors
- `ouster.urdf.xacro` - Ouster 3D LiDAR sensors
- `velodyne_puck.urdf.xacro` - Velodyne LiDAR
- `orbbec_astra.urdf.xacro` - Orbbec cameras
- `stereolabs_zed.urdf.xacro` - ZED cameras
- `luxonis_depthai.urdf.xacro` - OAK cameras
- `intel_realsense_d435.urdf.xacro` - RealSense cameras
- `teltonika_003R-00253.urdf.xacro` - GPS antenna
- `kinova.urdf.xacro` - Kinova manipulators
- `ur.urdf.xacro` - Universal Robots manipulators
- `robotiq.urdf.xacro` - Robotiq grippers
- `wibotic_receiver.urdf.xacro` - Wireless charging receiver

**To create or modify custom components:**

1. Edit existing URDF files or create new ones in `husarion_components_description/urdf/`
2. Rebuild the package:
   ```bash
   cd /home/sqlee/husarion00_ws
   colcon build --packages-select husarion_components_description
   source install/setup.bash
   ```
3. Update `components.yaml` to use your custom component