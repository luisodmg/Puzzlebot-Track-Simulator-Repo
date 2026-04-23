# v2 Python Clients (TE3002B Simulator)

This folder contains Python clients and gRPC definitions used to communicate with the TE3002B Unity simulator.

## Files

- `actividad_2_04.py`: professor version for Activity 2.04 (upload target). Same logic as `fulltest4.py`, with a different filename.
- `actividad_2_05.py`: professor version for Activity 2.05 (upload target). Same logic as `fulltest5.py`, with a different filename.
- `fulltest4.py`: full autonomous test node equivalent to `actividad_2_04.py`.
- `fulltest5.py`: full autonomous test node equivalent to `actividad_2_05.py`.
- `fulltest6.py`: work-in-progress traffic-sign prototype that streams camera frames, checks blur, runs YOLOv8n detection, and overlays the detected sign label.
- `client-rpc-tester.py`: baseline gRPC control loop that streams simulator frames, applies image noise preprocessing, and sends fixed motion commands for connectivity/latency checks.
- `client-ros2.py`: ROS2-to-simulator bridge that subscribes to `/cmd_vel`, forwards velocity commands over gRPC, and publishes simulator camera frames as ROS `Image` messages.
- `te3002b.proto`: protobuf service contract.
- `te3002b_pb2.py`, `te3002b_pb2_grpc.py`: generated Python bindings.

## Activity File Mapping

- Activity 2.04: `actividad_2_04.py` (professor naming) <-> `fulltest4.py` (full test node naming)
- Activity 2.05: `actividad_2_05.py` (professor naming) <-> `fulltest5.py` (full test node naming)

The logic is the same in each pair; only the filenames differ.

`fulltest6.py` is separate from those activity pairs. It is currently a prototype for traffic-sign detection and visualization, not a finished autonomous behavior loop.

## Prerequisites

- Python 3.9+
- Access to the simulator executable for your OS:
  - Windows: `../WinCtrl/TE3002BSim.exe`
  - macOS/Linux: use the corresponding simulator version for your platform

Install required Python packages:

```powershell
python -m pip install grpcio protobuf opencv-python numpy
```

For ROS2 client (`client-ros2.py`), you also need a ROS2 environment with:

- `rclpy`
- `sensor_msgs`
- `geometry_msgs`
- `cv_bridge`

## Connection

Clients connect to:

- Host: `127.0.0.1`
- Port: `7072`

Make sure the simulator is running before starting any script.

## Run

1. Start the simulator executable first (required):

On Windows:

```powershell
cd ..\WinCtrl
.\TE3002BSim.exe
```

On macOS/Linux, start the equivalent simulator build for your OS (not `WinCtrl`).

2. Open another terminal in this folder (`v2/`) and run one client:

```powershell
python .\client-rpc-tester.py
```

```powershell
python .\actividad_2_04.py
```

```powershell
python .\actividad_2_05.py
```

```powershell
python .\fulltest4.py
```

```powershell
python .\fulltest5.py
```

```powershell
python .\fulltest6.py
```

Current prototype behavior:

- initializes a gRPC connection to `127.0.0.1:7072`
- configures the simulator camera, robot reset, and scene selection
- runs frame acquisition in a background thread
- resizes the incoming image to a smaller preview for display
- uses a blur metric to skip low-quality frames before detection
- sends the frame through YOLOv8n (`yolov8n.pt`) and draws bounding boxes plus labels
- shows the latest detected sign as `En frente: ...`
- leaves the motion command at zero, so sign-based driving logic is still pending

The control behavior is intentionally incomplete at this stage.

For ROS2 mode (in a ROS2-enabled shell):

```powershell
python .\client-ros2.py
```

## Regenerate gRPC Code (if `te3002b.proto` changes)

```powershell
python -m pip install grpcio-tools
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. .\te3002b.proto
```

## Common Errors

- `UNAVAILABLE: failed to connect to all addresses`
  - Simulator not running yet.
- `ModuleNotFoundError` (`grpc`, `cv2`, `numpy`, etc.)
  - Install dependencies in the same Python environment you use to run scripts.
- ROS2 import errors in `client-ros2.py`
  - Run in a shell where ROS2 is properly sourced.
