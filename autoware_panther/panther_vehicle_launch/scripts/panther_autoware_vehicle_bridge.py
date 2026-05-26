#!/usr/bin/env python3

import math

import rclpy
from autoware_control_msgs.msg import Control
from autoware_vehicle_msgs.msg import (
    ControlModeReport,
    GearReport,
    HazardLightsReport,
    SteeringReport,
    TurnIndicatorsReport,
    VelocityReport,
)
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix


class PantherAutowareVehicleBridge(Node):
    def __init__(self) -> None:
        super().__init__("panther_autoware_vehicle_bridge")

        odom_topic = self.declare_parameter(
            "odom_topic", "/panther/odometry/wheels"
        ).get_parameter_value().string_value
        gps_fix_topic = self.declare_parameter(
            "gps_fix_topic", "/panther/gps/fix"
        ).get_parameter_value().string_value
        control_cmd_topic = self.declare_parameter(
            "control_cmd_topic", "/control/command/control_cmd"
        ).get_parameter_value().string_value
        cmd_vel_topic = self.declare_parameter(
            "cmd_vel_topic", "/panther/cmd_vel"
        ).get_parameter_value().string_value
        self._base_frame = self.declare_parameter(
            "base_frame", "base_link"
        ).get_parameter_value().string_value
        self._gnss_frame = self.declare_parameter(
            "gnss_frame", "gnss_base_link"
        ).get_parameter_value().string_value
        self._linear_deadband = self.declare_parameter(
            "linear_deadband", 0.01
        ).get_parameter_value().double_value
        self._angular_deadband = self.declare_parameter(
            "angular_deadband", 0.01
        ).get_parameter_value().double_value
        self._gnss_stamp_delay = self.declare_parameter(
            "gnss_stamp_delay", 1.0
        ).get_parameter_value().double_value
        self._wheel_base = self.declare_parameter(
            "wheel_base", 0.44
        ).get_parameter_value().double_value
        self._max_linear_velocity = self.declare_parameter(
            "max_linear_velocity", 1.5
        ).get_parameter_value().double_value
        self._max_angular_velocity = self.declare_parameter(
            "max_angular_velocity", 2.0
        ).get_parameter_value().double_value

        self._last_stamp = self.get_clock().now().to_msg()
        self._longitudinal_velocity = 0.0
        self._lateral_velocity = 0.0
        self._heading_rate = 0.0

        self._velocity_pub = self.create_publisher(
            VelocityReport, "/vehicle/status/velocity_status", 10
        )
        self._steering_pub = self.create_publisher(
            SteeringReport, "/vehicle/status/steering_status", 10
        )
        self._gear_pub = self.create_publisher(GearReport, "/vehicle/status/gear_status", 10)
        self._control_mode_pub = self.create_publisher(
            ControlModeReport, "/vehicle/status/control_mode", 10
        )
        self._turn_pub = self.create_publisher(
            TurnIndicatorsReport, "/vehicle/status/turn_indicators_status", 10
        )
        self._hazard_pub = self.create_publisher(
            HazardLightsReport, "/vehicle/status/hazard_lights_status", 10
        )
        self._fix_pub = self.create_publisher(NavSatFix, "/fix", 10)
        self._sensing_fix_pub = self.create_publisher(NavSatFix, "/sensing/gnss/fix", 10)
        self._cmd_vel_pub = self.create_publisher(Twist, cmd_vel_topic, 10)

        self._sub = self.create_subscription(Odometry, odom_topic, self._on_odom, 10)
        self._gps_sub = self.create_subscription(
            NavSatFix, gps_fix_topic, self._on_gps_fix, 10
        )
        self._control_sub = self.create_subscription(
            Control, control_cmd_topic, self._on_control_cmd, 10
        )
        self._timer = self.create_timer(0.1, self._publish_static_status)
        self.get_logger().info(f"Publishing Autoware vehicle status from {odom_topic}")
        self.get_logger().info(f"Relaying GNSS fix from {gps_fix_topic} to /fix")
        self.get_logger().info(f"Converting Autoware control: {control_cmd_topic} -> {cmd_vel_topic}")

    def _on_odom(self, msg: Odometry) -> None:
        self._last_stamp = msg.header.stamp
        twist = msg.twist.twist

        self._longitudinal_velocity = self._deadband(
            self._finite(twist.linear.x), self._linear_deadband
        )
        self._lateral_velocity = self._deadband(
            self._finite(twist.linear.y), self._linear_deadband
        )
        self._heading_rate = self._deadband(
            self._finite(twist.angular.z), self._angular_deadband
        )

    def _on_gps_fix(self, msg: NavSatFix) -> None:
        fix = NavSatFix()
        fix.header = msg.header
        stamp = self.get_clock().now() - Duration(seconds=self._gnss_stamp_delay)
        fix.header.stamp = stamp.to_msg()
        fix.header.frame_id = self._gnss_frame
        fix.status = msg.status
        fix.latitude = msg.latitude
        fix.longitude = msg.longitude
        fix.altitude = msg.altitude
        fix.position_covariance = msg.position_covariance
        fix.position_covariance_type = msg.position_covariance_type

        self._fix_pub.publish(fix)
        self._sensing_fix_pub.publish(fix)

    def _on_control_cmd(self, msg: Control) -> None:
        velocity = self._clamp(
            self._finite(msg.longitudinal.velocity),
            -self._max_linear_velocity,
            self._max_linear_velocity,
        )
        steering = self._finite(msg.lateral.steering_tire_angle)

        twist = Twist()
        twist.linear.x = velocity
        if abs(self._wheel_base) > 1e-6:
            angular = velocity * math.tan(steering) / self._wheel_base
        else:
            angular = 0.0
        twist.angular.z = self._clamp(
            angular, -self._max_angular_velocity, self._max_angular_velocity
        )
        self._cmd_vel_pub.publish(twist)

    def _publish_static_status(self) -> None:
        stamp = self.get_clock().now().to_msg()

        velocity = VelocityReport()
        velocity.header.stamp = self._last_stamp
        velocity.header.frame_id = self._base_frame
        velocity.longitudinal_velocity = self._longitudinal_velocity
        velocity.lateral_velocity = self._lateral_velocity
        velocity.heading_rate = self._heading_rate
        self._velocity_pub.publish(velocity)

        steering = SteeringReport()
        steering.stamp = self._last_stamp
        steering.steering_tire_angle = 0.0
        self._steering_pub.publish(steering)

        gear = GearReport()
        gear.stamp = stamp
        gear.report = GearReport.DRIVE
        self._gear_pub.publish(gear)

        control_mode = ControlModeReport()
        control_mode.stamp = stamp
        control_mode.mode = ControlModeReport.AUTONOMOUS
        self._control_mode_pub.publish(control_mode)

        turn = TurnIndicatorsReport()
        turn.stamp = stamp
        turn.report = TurnIndicatorsReport.DISABLE
        self._turn_pub.publish(turn)

        hazard = HazardLightsReport()
        hazard.stamp = stamp
        hazard.report = HazardLightsReport.DISABLE
        self._hazard_pub.publish(hazard)

    @staticmethod
    def _finite(value: float) -> float:
        return float(value) if math.isfinite(value) else 0.0

    @staticmethod
    def _deadband(value: float, threshold: float) -> float:
        return 0.0 if abs(value) < threshold else value

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))


def main() -> None:
    rclpy.init()
    node = PantherAutowareVehicleBridge()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()


if __name__ == "__main__":
    main()
