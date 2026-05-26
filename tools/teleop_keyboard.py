#!/usr/bin/env python3
"""
Keyboard teleop for a 4-wheel differential-drive (skid-steer) robot.

Differential drive has NO steering axle — turning is achieved by running
the left and right track/wheel sets at different speeds.  The Twist message
convention used here is:
  linear.x  > 0  → drive forward   (both sides forward)
  linear.x  < 0  → drive backward  (both sides backward)
  angular.z > 0  → rotate CCW/left (right side faster than left)
  angular.z < 0  → rotate CW/right (left side faster than right)

The node publishes geometry_msgs/Twist at a fixed rate so the robot's
watchdog timer keeps receiving commands even when no key is pressed.
"""

import argparse
import select
import sys
import termios
import tty
from dataclasses import dataclass, field

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node

# ──────────────────────────────────────────────────────────────────────────────
# Key-binding help text
# ──────────────────────────────────────────────────────────────────────────────
HELP = """
Keyboard Teleop — 4-Wheel Differential Drive
─────────────────────────────────────────────
Movement (skid-steer):

   i          Forward + turn left
   o          Forward
   p          Forward + turn right
   ←(j)       Rotate left (in-place)
   k          Stop
   l  →       Rotate right (in-place)
   m          Backward + turn left
   ,          Backward
   .          Backward + turn right

  (Alternatively use w/s for forward/back, a/d for in-place rotation)

Speed adjustment:
  q / z  : increase / decrease linear speed
  e / c  : increase / decrease angular speed
  r      : reset speeds to defaults

ESC or CTRL-C : stop robot and quit

Current speeds are printed whenever they change.
"""

# ──────────────────────────────────────────────────────────────────────────────
# Velocity command table
#   key → (linear_factor, angular_factor)
#   factors are multiplied by the current speed settings at runtime
# ──────────────────────────────────────────────────────────────────────────────
MOVE_BINDINGS: dict[str, tuple[float, float]] = {
    # ── forward/back only ────────────────────────────────
    "o": (50.0, 0.0),   # forward
    "w": (50.0, 0.0),
    ",": (-50.0, 0.0),  # backward
    "s": (-50.0, 0.0),
    # ── in-place rotation (differential drive core move) ─
    "j": (0.0, 50.0),   # rotate left CCW
    "a": (0.0, 50.0),
    "l": (0.0, -50.0),  # rotate right CW
    "d": (0.0, -50.0),
    # ── diagonal (linear + angular simultaneously) ────────
    "i": (50.0, 0.5),   # forward-left arc
    "p": (50.0, -0.5),  # forward-right arc
    "m": (-50.0, 0.5),  # backward-left arc
    ".": (-50.0, -0.5), # backward-right arc
    # ── stop ─────────────────────────────────────────────
    "k": (0.0, 0.0),
    "x": (0.0, 0.0),
}

SPEED_STEP_LINEAR  = 0.05   # m/s per key press
SPEED_STEP_ANGULAR = 0.1    # rad/s per key press


# ──────────────────────────────────────────────────────────────────────────────
# ROS 2 node
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class SpeedConfig:
    linear:      float
    angular:     float
    max_linear:  float
    max_angular: float
    default_linear:  float = field(init=False)
    default_angular: float = field(init=False)

    def __post_init__(self):
        self.default_linear  = self.linear
        self.default_angular = self.angular

    def reset(self):
        self.linear  = self.default_linear
        self.angular = self.default_angular


class KeyboardTeleop(Node):
    def __init__(self, topic: str, cfg: SpeedConfig, rate_hz: float):
        super().__init__("keyboard_teleop")

        self.pub   = self.create_publisher(Twist, topic, 10)
        self.cfg   = cfg
        self._lin  = 0.0   # current commanded linear velocity  [m/s]
        self._ang  = 0.0   # current commanded angular velocity [rad/s]

        # Periodic publisher — keeps robot watchdog alive even without input.
        self.timer = self.create_timer(50.0 / rate_hz, self._publish)

        self.get_logger().info(f"Publishing Twist on '{topic}' @ {rate_hz:.0f} Hz")
        self.get_logger().info(
            f"Speed — linear: {cfg.linear:.2f} m/s  "
            f"angular: {cfg.angular:.2f} rad/s  "
            f"(max {cfg.max_linear:.2f} / {cfg.max_angular:.2f})"
        )

    # ── velocity command ──────────────────────────────────────────────────────

    def set_cmd(self, lin_factor: float, ang_factor: float):
        """Apply move-binding factors, clamp to limits, store."""
        self._lin = max(
            -self.cfg.max_linear,
            min(self.cfg.max_linear, lin_factor * self.cfg.linear),
        )
        self._ang = max(
            -self.cfg.max_angular,
            min(self.cfg.max_angular, ang_factor * self.cfg.angular),
        )
        self._publish()  # flush immediately — don't wait for the timer tick

    def stop(self):
        self._lin = 0.0
        self._ang = 0.0
        self._publish()

    def _publish(self):
        msg = Twist()
        msg.linear.x  = self._lin
        msg.angular.z = self._ang
        self.pub.publish(msg)

    # ── speed adjustment ──────────────────────────────────────────────────────

    def adjust_linear(self, delta: float):
        self.cfg.linear = max(
            SPEED_STEP_LINEAR,
            min(self.cfg.max_linear, self.cfg.linear + delta),
        )
        print(f"  linear_speed  = {self.cfg.linear:.2f} m/s")

    def adjust_angular(self, delta: float):
        self.cfg.angular = max(
            SPEED_STEP_ANGULAR,
            min(self.cfg.max_angular, self.cfg.angular + delta),
        )
        print(f"  angular_speed = {self.cfg.angular:.2f} rad/s")

    def reset_speeds(self):
        self.cfg.reset()
        print(
            f"  Speeds reset — "
            f"linear: {self.cfg.linear:.2f}  angular: {self.cfg.angular:.2f}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Raw-mode key reader
# ──────────────────────────────────────────────────────────────────────────────

def get_key(timeout: float = 0.05) -> str:
    """Return a single character from stdin without blocking longer than timeout."""
    dr, _, _ = select.select([sys.stdin], [], [], timeout)
    if dr:
        return sys.stdin.read(1)
    return ""


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Keyboard teleop for a 4-wheel differential-drive robot."
    )
    parser.add_argument(
        "--topic", default="/cmd_vel",
        help="Twist topic name (default: /cmd_vel)",
    )
    parser.add_argument(
        "--linear", type=float, default=0.6,
        help="Initial linear speed in m/s (default: 0.6)",
    )
    parser.add_argument(
        "--angular", type=float, default=50.0,
        help="Initial angular speed in rad/s (default: 50.0)",
    )
    parser.add_argument(
        "--max-linear", type=float, default=1.5,
        help="Maximum linear speed in m/s (default: 1.5)",
    )
    parser.add_argument(
        "--max-angular", type=float, default=3.0,
        help="Maximum angular speed in rad/s (default: 3.0)",
    )
    parser.add_argument(
        "--rate", type=float, default=20.0,
        help="Publish rate in Hz (default: 20)",
    )
    args = parser.parse_args()

    cfg = SpeedConfig(
        linear=args.linear,
        angular=args.angular,
        max_linear=args.max_linear,
        max_angular=args.max_angular,
    )

    # Save terminal settings so we can restore them on exit.
    saved_settings = termios.tcgetattr(sys.stdin)

    rclpy.init()
    node = KeyboardTeleop(args.topic, cfg, args.rate)

    print(HELP)

    try:
        tty.setcbreak(sys.stdin.fileno())

        while rclpy.ok():
            key = get_key()

            if key in MOVE_BINDINGS:
                lin_f, ang_f = MOVE_BINDINGS[key]
                node.set_cmd(lin_f, ang_f)

            elif key == "q":
                node.adjust_linear(+SPEED_STEP_LINEAR)
            elif key == "z":
                node.adjust_linear(-SPEED_STEP_LINEAR)
            elif key == "e":
                node.adjust_angular(+SPEED_STEP_ANGULAR)
            elif key == "c":
                node.adjust_angular(-SPEED_STEP_ANGULAR)
            elif key == "r":
                node.reset_speeds()

            elif key in ("\x03", "\x1b"):   # CTRL-C or ESC
                break

            rclpy.spin_once(node, timeout_sec=0.0)

    finally:
        node.stop()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, saved_settings)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()