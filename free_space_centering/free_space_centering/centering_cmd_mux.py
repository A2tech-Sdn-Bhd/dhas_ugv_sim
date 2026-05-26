"""
Relay the free-space centering Twist to Panther with safety limits.

The free_space_centering node publishes its suggested linear.x and angular.z on
/cmd_vel_centering. This node clamps those values, keeps a minimum forward speed
when centered, and republishes them to the Panther command topic.
"""

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


class CenteringCmdMux(Node):
    def __init__(self):
        super().__init__("centering_cmd_mux")

        self.declare_parameter("centering_cmd_topic", "/cmd_vel_centering")
        self.declare_parameter("output_cmd_topic", "/panther/cmd_vel")
        self.declare_parameter("min_forward_speed", 0.50)
        self.declare_parameter("max_linear_speed", 2.0)
        self.declare_parameter("allow_reverse", False)
        self.declare_parameter("max_angular_speed", 1.0)
        self.declare_parameter("command_timeout_sec", 0.5)
        self.declare_parameter("publish_rate_hz", 20.0)

        centering_topic = self.get_parameter("centering_cmd_topic").value
        output_topic = self.get_parameter("output_cmd_topic").value
        self._min_forward_speed = float(self.get_parameter("min_forward_speed").value)
        self._max_linear_speed = float(self.get_parameter("max_linear_speed").value)
        self._allow_reverse = bool(self.get_parameter("allow_reverse").value)
        self._max_angular_speed = float(self.get_parameter("max_angular_speed").value)
        self._timeout_sec = float(self.get_parameter("command_timeout_sec").value)
        publish_rate_hz = float(self.get_parameter("publish_rate_hz").value)

        self._last_linear_x = 0.0
        self._last_angular_z = 0.0
        self._last_centering_time = None

        self.create_subscription(Twist, centering_topic, self._on_centering_cmd, 10)
        self._cmd_pub = self.create_publisher(Twist, output_topic, 10)
        self.create_timer(1.0 / publish_rate_hz, self._publish_cmd)

        self.get_logger().info(
            f"Centering mux ready: {centering_topic} Twist -> {output_topic}, "
            f"min forward {self._min_forward_speed:.2f} m/s, "
            f"max linear {self._max_linear_speed:.2f} m/s, "
            f"max angular {self._max_angular_speed:.2f} rad/s"
        )

    def _on_centering_cmd(self, msg: Twist) -> None:
        min_linear_speed = -self._max_linear_speed if self._allow_reverse else 0.0
        suggested_linear_x = self._clamp(
            float(msg.linear.x),
            min_linear_speed,
            self._max_linear_speed,
        )
        if not self._allow_reverse:
            suggested_linear_x = max(suggested_linear_x, self._min_forward_speed)

        self._last_linear_x = suggested_linear_x
        self._last_angular_z = self._clamp(
            float(msg.angular.z),
            -self._max_angular_speed,
            self._max_angular_speed,
        )
        self._last_centering_time = self.get_clock().now()

    def _publish_cmd(self) -> None:
        twist = Twist()

        if self._last_centering_time is not None:
            age = (self.get_clock().now() - self._last_centering_time).nanoseconds / 1e9
            if age <= self._timeout_sec:
                twist.linear.x = self._last_linear_x
                twist.angular.z = self._last_angular_z

        self._cmd_pub.publish(twist)

    @staticmethod
    def _clamp(value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))

    
def main(args=None):
    rclpy.init(args=args)
    node = CenteringCmdMux()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
