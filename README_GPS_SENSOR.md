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
husarion_components_description/urdf/
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