cmake_minimum_required(VERSION 3.14)
project(panther_vehicle_launch)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/panther_autoware_vehicle_bridge.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
