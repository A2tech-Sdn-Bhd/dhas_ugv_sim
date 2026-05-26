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

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    gps_topic = LaunchConfiguration('gps_topic')
    output_path = LaunchConfiguration('output_path')
    sample_period_sec = LaunchConfiguration('sample_period_sec')

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'gps_topic',
                default_value='/panther/gps/filtered',
                description='NavSatFix topic to sample.',
            ),
            DeclareLaunchArgument(
                'output_path',
                default_value='gps_coordinates.json',
                description='JSON file where GPS samples are stored.',
            ),
            DeclareLaunchArgument(
                'sample_period_sec',
                default_value='1.0',
                description='Seconds between stored GPS samples.',
            ),
            Node(
                package='gps_coordinate_logger',
                executable='gps_coordinate_logger',
                name='gps_coordinate_logger',
                output='screen',
                parameters=[
                    {
                        'gps_topic': gps_topic,
                        'output_path': output_path,
                        'sample_period_sec': sample_period_sec,
                    }
                ],
            ),
        ]
    )
