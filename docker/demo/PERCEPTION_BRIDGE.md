# Perception Bridge for Autoware

This bridge relays Husarion simulation topics into Autoware-friendly sensing topic names.

## Topics

- `/<ROBOT_NAMESPACE>/lidar_3d/ouster/points` -> `/sensing/lidar/top/pointcloud_raw`
- `/<ROBOT_NAMESPACE>/front_cam/color/image_raw` -> `/sensing/camera/front/image_raw`
- `/<ROBOT_NAMESPACE>/front_cam/color/camera_info` -> `/sensing/camera/front/camera_info`
- `/<ROBOT_NAMESPACE>/front_cam/depth/image_raw` -> `/sensing/camera/front/depth/image_raw`
- `/<ROBOT_NAMESPACE>/front_cam/depth/camera_info` -> `/sensing/camera/front/depth/camera_info`

## Run

From `docker/demo`:

```bash
xhost local:docker
docker compose -f compose.simulation.gps.yaml -f compose.perception.bridge.yaml up -d
```

If you do not need GPS stack, use:

```bash
docker compose -f compose.simulation.yaml -f compose.perception.bridge.yaml up -d
```

## Validate

```bash
docker exec -it autoware_topic_bridge ros2 topic list | grep sensing
docker exec -it autoware_topic_bridge ros2 topic hz /sensing/lidar/top/pointcloud_raw
docker exec -it autoware_topic_bridge ros2 topic hz /sensing/camera/front/image_raw
```

## Notes

- Namespace defaults to `panther` via `ROBOT_NAMESPACE`.
- Set `ROBOT_NAMESPACE=<name>` before `docker compose up` for multi-robot runs.
