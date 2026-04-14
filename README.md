# v2 Python Clients (TE3002B Simulator)

This folder contains Python clients and gRPC definitions used to communicate with the TE3002B Unity simulator.

## Files

- `actividad_2_04.py`: standalone gRPC client that receives frames and sends motion commands.
- `client-rpc-tester.py`: simple RPC test client.
- `client-ros2.py`: ROS2 bridge client (`/cmd_vel` subscriber, `Image` publisher).
- `te3002b.proto`: protobuf service contract.
- `te3002b_pb2.py`, `te3002b_pb2_grpc.py`: generated Python bindings.

## Prerequisites

- Python 3.9+
- Access to the simulator executable at `../WinCtrl/TE3002BSim.exe`

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

```powershell
cd ..\WinCtrl
.\TE3002BSim.exe
```

2. Open another terminal in this folder (`v2/`) and run one client:

```powershell
python .\client-rpc-tester.py
```

```powershell
python .\actividad_2_04.py
```

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
