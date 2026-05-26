#!/usr/bin/env python3

import math
import struct

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField


class LidarPointTypeAdapter(Node):
    def __init__(self) -> None:
        super().__init__("lidar_point_type_adapter")

        in_topic = self.declare_parameter(
            "input_topic", "/panther/lidar_3d/ouster/points"
        ).get_parameter_value().string_value
        out_topic = self.declare_parameter(
            "output_topic", "/sensing/lidar/top/pointcloud_raw"
        ).get_parameter_value().string_value
        self._output_frame = self.declare_parameter(
            "output_frame", "velodyne_top"
        ).get_parameter_value().string_value

        self._sub = self.create_subscription(PointCloud2, in_topic, self._cb, 10)
        self._pub = self.create_publisher(PointCloud2, out_topic, 10)
        self.get_logger().info(
            f"Adapting point cloud: {in_topic} -> {out_topic} ({self._output_frame})"
        )

    def _cb(self, msg: PointCloud2) -> None:
        fields = {f.name: (f.offset, f.datatype) for f in msg.fields}
        required = ["x", "y", "z", "intensity", "ring"]
        missing = [name for name in required if name not in fields]
        if missing:
            self.get_logger().error(f"Input cloud missing fields: {missing}")
            return

        x_off, _ = fields["x"]
        y_off, _ = fields["y"]
        z_off, _ = fields["z"]
        i_off, i_type = fields["intensity"]
        r_off, r_type = fields["ring"]

        in_step = msg.point_step
        n_points = msg.width * msg.height
        in_data = msg.data

        # Autoware PointXYZIRC layout: x,y,z,float + uint8 + uint8 + uint16
        out_step = 16
        out_data = bytearray(n_points * out_step)

        for idx in range(n_points):
            ib = idx * in_step
            ob = idx * out_step

            x = struct.unpack_from("<f", in_data, ib + x_off)[0]
            y = struct.unpack_from("<f", in_data, ib + y_off)[0]
            z = struct.unpack_from("<f", in_data, ib + z_off)[0]

            if not math.isfinite(x) or not math.isfinite(y) or not math.isfinite(z):
                # Keep cloud dense for downstream filters. Replace invalid points
                # with neutral values that will be removed by crop / range filters.
                x = 0.0
                y = 0.0
                z = 0.0

            if i_type == PointField.FLOAT32:
                i_f = struct.unpack_from("<f", in_data, ib + i_off)[0]
                intensity = 0 if math.isnan(i_f) else int(max(0, min(255, round(i_f))))
            elif i_type == PointField.UINT8:
                intensity = int(in_data[ib + i_off])
            elif i_type == PointField.UINT16:
                intensity = min(255, struct.unpack_from("<H", in_data, ib + i_off)[0])
            else:
                intensity = 0

            if r_type == PointField.UINT16:
                channel = struct.unpack_from("<H", in_data, ib + r_off)[0]
            elif r_type == PointField.UINT8:
                channel = int(in_data[ib + r_off])
            else:
                channel = 0

            struct.pack_into("<fff", out_data, ob + 0, x, y, z)
            struct.pack_into("<B", out_data, ob + 12, intensity)
            struct.pack_into("<B", out_data, ob + 13, 0)  # return_type
            struct.pack_into("<H", out_data, ob + 14, channel)

        out = PointCloud2()
        out.header = msg.header
        out.header.frame_id = self._output_frame
        out.height = msg.height
        out.width = msg.width
        out.fields = [
            PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1),
            PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1),
            PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1),
            PointField(name="intensity", offset=12, datatype=PointField.UINT8, count=1),
            PointField(name="return_type", offset=13, datatype=PointField.UINT8, count=1),
            PointField(name="channel", offset=14, datatype=PointField.UINT16, count=1),
        ]
        out.is_bigendian = False
        out.point_step = out_step
        out.row_step = out_step * out.width
        out.is_dense = True
        out.data = bytes(out_data)
        self._pub.publish(out)


def main() -> None:
    rclpy.init()
    node = LidarPointTypeAdapter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
