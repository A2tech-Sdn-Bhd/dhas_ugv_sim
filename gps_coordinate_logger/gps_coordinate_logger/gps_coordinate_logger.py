# Copyright 2026 A2Tech
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""ROS 2 node for recording filtered GPS coordinates to JSON."""

import json
import math
from pathlib import Path
from typing import Any

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix


class GpsCoordinateLogger(Node):
    """Sample the latest GPS fix and store coordinates in a JSON file."""

    def __init__(self) -> None:
        super().__init__('gps_coordinate_logger')

        self.declare_parameter('gps_topic', '/panther/gps/filtered')
        self.declare_parameter('output_path', 'gps_coordinates.json')
        self.declare_parameter('sample_period_sec', 1.0)

        self._gps_topic = self.get_parameter('gps_topic').value
        self._output_path = Path(self.get_parameter('output_path').value).expanduser()
        self._sample_period_sec = float(self.get_parameter('sample_period_sec').value)

        if self._sample_period_sec <= 0.0:
            raise ValueError('sample_period_sec must be greater than 0')

        self._latest_fix: NavSatFix | None = None
        self._samples: list[dict[str, Any]] = self._load_existing_samples()

        self.create_subscription(NavSatFix, self._gps_topic, self._gps_callback, 10)
        self.create_timer(self._sample_period_sec, self._sample_latest_fix)

        self.get_logger().info(
            'Logging GPS samples from '
            f'{self._gps_topic} every {self._sample_period_sec:.2f}s '
            f'to {self._output_path}'
        )

    def _gps_callback(self, msg: NavSatFix) -> None:
        self._latest_fix = msg

    def _sample_latest_fix(self) -> None:
        if self._latest_fix is None:
            self.get_logger().warn(
                'Waiting for first GPS fix',
                throttle_duration_sec=5.0,
            )
            return

        msg = self._latest_fix
        sample_time = self.get_clock().now().to_msg()
        if not self._is_valid_coordinate(msg):
            self.get_logger().warn('Skipping GPS fix with invalid coordinates')
            return

        sample = {
            'sample_time': {
                'sec': sample_time.sec,
                'nanosec': sample_time.nanosec,
            },
            'gps_stamp': {
                'sec': msg.header.stamp.sec,
                'nanosec': msg.header.stamp.nanosec,
            },
            'frame_id': msg.header.frame_id,
            'status': {
                'status': msg.status.status,
                'service': msg.status.service,
            },
            'latitude': msg.latitude,
            'longitude': msg.longitude,
            'altitude': msg.altitude,
            'position_covariance': list(msg.position_covariance),
            'position_covariance_type': msg.position_covariance_type,
        }

        self._samples.append(sample)
        self._write_samples()
        self.get_logger().info(
            f'Stored GPS sample #{len(self._samples)}: '
            f'lat={msg.latitude:.8f}, lon={msg.longitude:.8f}, '
            f'alt={msg.altitude:.3f}',
            throttle_duration_sec=1.0,
        )

    def _load_existing_samples(self) -> list[dict[str, Any]]:
        if not self._output_path.exists():
            return []

        try:
            with self._output_path.open('r', encoding='utf-8') as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            self.get_logger().warn(
                f'Could not read existing JSON file {self._output_path}: {exc}. '
                'Starting fresh.'
            )
            return []

        if isinstance(data, list):
            return data

        self.get_logger().warn(
            f'Existing JSON file {self._output_path} does not contain a list. '
            'Starting fresh.'
        )
        return []

    def _write_samples(self) -> None:
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._output_path.with_suffix(
            self._output_path.suffix + '.tmp'
        )

        with temporary_path.open('w', encoding='utf-8') as file:
            json.dump(self._samples, file, indent=2)
            file.write('\n')

        temporary_path.replace(self._output_path)

    @staticmethod
    def _is_valid_coordinate(msg: NavSatFix) -> bool:
        return (
            math.isfinite(msg.latitude)
            and math.isfinite(msg.longitude)
            and math.isfinite(msg.altitude)
        )


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = GpsCoordinateLogger()

    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
