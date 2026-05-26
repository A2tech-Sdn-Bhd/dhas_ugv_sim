"""
free_space_centering.py
=======================
ROS 2 node that reads /perception/occupancy_grid_map/map and publishes
geometry_msgs/Twist commands to keep the robot centered in free space.

Usage
-----
  ros2 run <your_package> free_space_centering

Subscribed topics
-----------------
  /perception/occupancy_grid_map/map          (nav_msgs/OccupancyGrid)
  /perception/occupancy_grid_map/map_updates  (map_msgs/OccupancyGridUpdate)
  /tf                                          (for robot pose in map frame)

Published topics
----------------
  /cmd_vel_centering   (geometry_msgs/Twist)  — velocity correction command
  ~/free_space_marker  (visualization_msgs/Marker) — centroid marker for RViz

Parameters
----------
  robot_frame       (str,   default: "base_link")  — robot TF frame
  map_frame         (str,   default: "map")         — map TF frame
  search_radius_m   (float, default: 5.0)           — radius to scan for free cells (metres)
  gain_linear       (float, default: 0.3)           — P-gain: m/s per metre of offset
  max_linear_speed  (float, default: 0.5)           — clamp on linear velocity (m/s)
  max_angular_speed (float, default: 0.6)           — clamp on angular velocity (rad/s)
  centering_thresh  (float, default: 0.15)          — offset (m) below which no correction sent
  publish_rate_hz   (float, default: 10.0)          — control loop rate
"""

import math
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.duration import Duration

from nav_msgs.msg import OccupancyGrid
from map_msgs.msg import OccupancyGridUpdate
from geometry_msgs.msg import Twist
from visualization_msgs.msg import Marker
from std_msgs.msg import ColorRGBA

try:
    from tf2_ros import Buffer, TransformListener, LookupException, ConnectivityException, ExtrapolationException
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False


class FreeSpaceCenteringNode(Node):
    """
    Algorithm
    ---------
    Every control tick:
      1. Look up robot pose in map frame via TF.
      2. Convert robot world position → grid cell (col, row).
      3. Iterate all cells within search_radius_m.
      4. Collect cells whose occupancy value == 0 (free).
      5. Compute their centroid in world coordinates.
      6. Vector from robot to centroid = correction direction.
      7. Scale by gain → linear velocity; rotate heading toward centroid → angular velocity.
      8. Clamp and publish Twist.
    """

    def __init__(self):
        super().__init__("free_space_centering")

        # ── Parameters ──────────────────────────────────────────────────────
        self.declare_parameter("robot_frame",       "base_link")
        self.declare_parameter("map_frame",         "map")
        self.declare_parameter("search_radius_m",   5.0)
        self.declare_parameter("gain_linear",       1.2)
        self.declare_parameter("max_linear_speed",  2.0)
        self.declare_parameter("max_angular_speed", 1.0)
        self.declare_parameter("centering_thresh",  0.15)
        self.declare_parameter("publish_rate_hz",   10.0)
        self.declare_parameter("free_threshold", 50)
        self.declare_parameter("forward_sector_deg", 180.0)
        
        self._free_thresh = self.get_parameter("free_threshold").value
        self._robot_frame      = self.get_parameter("robot_frame").value
        self._map_frame        = self.get_parameter("map_frame").value
        self._search_radius    = self.get_parameter("search_radius_m").value
        self._gain             = self.get_parameter("gain_linear").value
        self._max_v            = self.get_parameter("max_linear_speed").value
        self._max_w            = self.get_parameter("max_angular_speed").value
        self._thresh           = self.get_parameter("centering_thresh").value
        self._forward_sector_deg = float(self.get_parameter("forward_sector_deg").value)
        self._forward_sector_deg = self._clamp(self._forward_sector_deg, 1.0, 360.0)
        rate_hz                = self.get_parameter("publish_rate_hz").value

        # ── Internal state ───────────────────────────────────────────────────
        self._grid: OccupancyGrid | None = None   # latest full map
        self._grid_data: np.ndarray | None = None  # shape (height, width), int8

        # ── TF ───────────────────────────────────────────────────────────────
        if TF_AVAILABLE:
            self._tf_buffer   = Buffer()
            self._tf_listener = TransformListener(self._tf_buffer, self)
        else:
            self.get_logger().warn("tf2_ros not available — robot pose assumed at map origin.")

        # ── Subscriptions ────────────────────────────────────────────────────
        self.create_subscription(
            OccupancyGrid,
            "/perception/occupancy_grid_map/map",
            self._on_full_map,
            10,
        )
        self.create_subscription(
            OccupancyGridUpdate,
            "/perception/occupancy_grid_map/map_updates",
            self._on_map_update,
            10,
        )

        # ── Publishers ───────────────────────────────────────────────────────
        self._cmd_pub = self.create_publisher(Twist, "/cmd_vel_centering", 10)
        self._marker_pub = self.create_publisher(
            Marker, "~/free_space_marker", 10
        )

        # ── Control timer ────────────────────────────────────────────────────
        self.create_timer(1.0 / rate_hz, self._control_tick)

        self.get_logger().info(
            f"FreeSpaceCentering ready — search radius {self._search_radius} m, "
            f"gain {self._gain}, max v {self._max_v} m/s"
        )

    # ────────────────────────────────────────────────────────────────────────
    # Map callbacks
    # ────────────────────────────────────────────────────────────────────────

    def _on_full_map(self, msg: OccupancyGrid) -> None:
        """Replace the entire local grid copy."""
        self._grid = msg
        self._grid_data = np.array(msg.data, dtype=np.int8).reshape(
            msg.info.height, msg.info.width
        )

    def _on_map_update(self, msg: OccupancyGridUpdate) -> None:
        """Apply an incremental patch to the local grid copy (bandwidth-efficient)."""
        if self._grid is None or self._grid_data is None:
            return
        # Validate dimensions match
        if (msg.x + msg.width  > self._grid.info.width or
                msg.y + msg.height > self._grid.info.height):
            self.get_logger().warn("Map update patch exceeds stored grid bounds — ignored.")
            return
        patch = np.array(msg.data, dtype=np.int8).reshape(msg.height, msg.width)
        self._grid_data[msg.y: msg.y + msg.height, msg.x: msg.x + msg.width] = patch

    # ────────────────────────────────────────────────────────────────────────
    # Control loop
    # ────────────────────────────────────────────────────────────────────────

    def _control_tick(self) -> None:
        if self._grid is None or self._grid_data is None:
            return  # no map yet

        # 1. Robot pose in map frame
        robot_x, robot_y, robot_yaw = self._get_robot_pose()
        if robot_x is None:
            return

        # 2. Compute free-space centroid
        result = self._compute_free_centroid(robot_x, robot_y, robot_yaw)
        if result is None:
            self.get_logger().warn("No free cells found within search radius!", throttle_duration_sec=5.0)
            return

        centroid_x, centroid_y, free_cell_count = result

        # 3. Correction vector in map frame
        dx = centroid_x - robot_x
        dy = centroid_y - robot_y
        distance = math.hypot(dx, dy)

        self.get_logger().info(
            f"Free cells: {free_cell_count} | centroid offset: "
            f"dx={dx:.3f} m  dy={dy:.3f} m  dist={distance:.3f} m",
            throttle_duration_sec=1.0,
        )

        # 4. Publish centroid marker for RViz
        self._publish_marker(centroid_x, centroid_y, distance)

        # 5. Build Twist
        twist = Twist()
        if distance > self._thresh:
            # Angle to centroid in map frame, then relative to robot heading
            angle_to_centroid = math.atan2(dy, dx)
            heading_error     = self._wrap_angle(angle_to_centroid - robot_yaw)

            # Linear speed proportional to distance, projected on robot's forward axis
            v = self._clamp(self._gain * distance * math.cos(heading_error),
                            -self._max_v, self._max_v)
            # Angular speed proportional to heading error
            w = self._clamp(self._gain * 2.0 * heading_error,
                            -self._max_w, self._max_w)

            twist.linear.x  = float(v)
            twist.angular.z = float(w)

        self._cmd_pub.publish(twist)

    # ────────────────────────────────────────────────────────────────────────
    # Core algorithm: free-space centroid
    # ────────────────────────────────────────────────────────────────────────

    def _compute_free_centroid(
        self, robot_world_x: float, robot_world_y: float, robot_yaw: float
    ) -> tuple[float, float, int] | None:
        """
        Returns (centroid_world_x, centroid_world_y, free_cell_count) or None.

        Steps
        -----
        1. Convert robot world pos → grid cell indices.
        2. Compute search window in cell space from search_radius_m.
        3. Build a boolean mask: free cells within radius.
        4. Compute centroid of masked cells.
        5. Convert centroid cell back to world coordinates.
        """
        info = self._grid.info
        res  = info.resolution
        ox   = info.origin.position.x
        oy   = info.origin.position.y
        W    = info.width
        H    = info.height

        # Robot cell
        robot_col = int((robot_world_x - ox) / res)
        robot_row = int((robot_world_y - oy) / res)

        # Search window bounds (clamped to grid)
        radius_cells = int(math.ceil(self._search_radius / res))
        col_min = max(0,   robot_col - radius_cells)
        col_max = min(W-1, robot_col + radius_cells)
        row_min = max(0,   robot_row - radius_cells)
        row_max = min(H-1, robot_row + radius_cells)

        # Sub-grid slice
        sub = self._grid_data[row_min:row_max+1, col_min:col_max+1]

        # Column and row index arrays relative to sub-grid
        cols = np.arange(col_min, col_max + 1)
        rows = np.arange(row_min, row_max + 1)
        col_grid, row_grid = np.meshgrid(cols, rows)

        # Distance mask (circular search region)
        dist_sq = (col_grid - robot_col)**2 + (row_grid - robot_row)**2
        in_radius = dist_sq <= radius_cells**2

        # Build a forward-sector mask in world/map frame, centered on robot heading.
        cell_world_x = ox + (col_grid + 0.5) * res
        cell_world_y = oy + (row_grid + 0.5) * res
        rel_x = cell_world_x - robot_world_x
        rel_y = cell_world_y - robot_world_y
        cell_bearing = np.arctan2(rel_y, rel_x)
        rel_bearing = np.arctan2(
            np.sin(cell_bearing - robot_yaw),
            np.cos(cell_bearing - robot_yaw),
        )
        half_fov = math.radians(self._forward_sector_deg) * 0.5
        in_forward_sector = np.abs(rel_bearing) <= half_fov

        # Free mask: free, within search radius, and inside the forward sector.
        free_mask = (sub < self._free_thresh) & in_radius & in_forward_sector


        free_count = int(np.sum(free_mask))
        if free_count == 0:
            return None

        # Centroid in cell space
        centroid_col = float(np.sum(col_grid[free_mask])) / free_count
        centroid_row = float(np.sum(row_grid[free_mask])) / free_count

        # Convert back to world coordinates (cell centre)
        centroid_world_x = ox + (centroid_col + 0.5) * res
        centroid_world_y = oy + (centroid_row + 0.5) * res

        return centroid_world_x, centroid_world_y, free_count

    # ────────────────────────────────────────────────────────────────────────
    # TF helper
    # ────────────────────────────────────────────────────────────────────────

    def _get_robot_pose(self) -> tuple[float | None, float | None, float | None]:
        """Return (x, y, yaw) of robot in map frame, or (None, None, None) on failure."""
        if not TF_AVAILABLE:
            return 0.0, 0.0, 0.0  # fallback: assume robot at origin

        try:
            tf = self._tf_buffer.lookup_transform(
                self._map_frame,
                self._robot_frame,
                rclpy.time.Time(),
                timeout=Duration(seconds=0.1),
            )
        except (LookupException, ConnectivityException, ExtrapolationException) as e:
            self.get_logger().warn(f"TF lookup failed: {e}", throttle_duration_sec=2.0)
            return None, None, None

        t = tf.transform.translation
        q = tf.transform.rotation
        # Extract yaw from quaternion
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        return t.x, t.y, yaw

    # ────────────────────────────────────────────────────────────────────────
    # RViz marker
    # ────────────────────────────────────────────────────────────────────────

    def _publish_marker(self, x: float, y: float, dist: float) -> None:
        m = Marker()
        m.header.frame_id = self._map_frame
        m.header.stamp    = self.get_clock().now().to_msg()
        m.ns              = "free_space_centroid"
        m.id              = 0
        m.type            = Marker.SPHERE
        m.action          = Marker.ADD
        m.pose.position.x = x
        m.pose.position.y = y
        m.pose.position.z = 0.1
        m.pose.orientation.w = 1.0
        m.scale.x = m.scale.y = m.scale.z = 0.3
        # Green when centered, yellow when offset
        if dist < self._thresh:
            m.color = ColorRGBA(r=0.2, g=0.9, b=0.3, a=0.9)
        else:
            m.color = ColorRGBA(r=1.0, g=0.75, b=0.0, a=0.9)
        self._marker_pub.publish(m)

    # ────────────────────────────────────────────────────────────────────────
    # Utilities
    # ────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _wrap_angle(a: float) -> float:
        """Wrap angle to [-π, π]."""
        return math.atan2(math.sin(a), math.cos(a))

    @staticmethod
    def _clamp(val: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, val))


# ────────────────────────────────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────────────────────────────────

def main(args=None):
    rclpy.init(args=args)
    node = FreeSpaceCenteringNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
