"""
main.py — SimRobotNode wired to the custom traffic sign detector.

Run:
    python main.py

Press Q in the OpenCV window to stop.
"""

import threading
import time

import cv2
import numpy as np
import grpc
import google.protobuf.empty_pb2

import te3002b_pb2
import te3002b_pb2_grpc

from detector import TrafficSignDetection

# ── Robot config ──────────────────────────────────────────────────────────────
GRPC_ADDR    = "127.0.0.1:7072"
CAM_W, CAM_H = 360, 240
OUT_W, OUT_H = 320, 240
SCENE        = 2026
TIMER_DELTA  = 0.025
# ─────────────────────────────────────────────────────────────────────────────


class SimRobotNode:
    def __init__(self):
        self.channel  = grpc.insecure_channel(GRPC_ADDR)
        self.stub     = te3002b_pb2_grpc.TE3002BSimStub(self.channel)

        self.cv_image    = None
        self.datacmd     = te3002b_pb2.CommandData()
        self.dataconfig  = te3002b_pb2.ConfigurationData()
        self.twist       = [0.0] * 6
        self.running     = True
        self.running_time = 0.0

        # Plug in the detector
        self.detector = TrafficSignDetection()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _set_twist(self, lx=0.0, ly=0.0, lz=0.0, ax=0.0, ay=0.0, az=0.0):
        self.twist = [lx, ly, lz, ax, ay, az]
        self.datacmd.linear.x  = lx
        self.datacmd.linear.y  = ly
        self.datacmd.linear.z  = lz
        self.datacmd.angular.x = ax
        self.datacmd.angular.y = ay
        self.datacmd.angular.z = az
        self.stub.SetCommand(self.datacmd)

    def _decide_action(self, sign: str):
        """
        Map detected sign → robot velocity command.
        Extend this as needed for your activity.
        """
        if sign == "Stop":
            self._set_twist()                    # full stop
        elif sign == "Go Straight":
            self._set_twist(lx=0.2)              # move forward
        elif sign == "Turn Left/Right":
            self._set_twist(lx=0.1, az=0.5)     # gentle left turn
        elif sign == "Workers":
            self._set_twist(lx=0.1)              # slow down
        else:
            self._set_twist()                    # default: stop

    # ── Main loop ─────────────────────────────────────────────────────────────
    def callback(self):
        # Configure simulator
        cfg = self.dataconfig
        cfg.resetRobot     = True
        cfg.mode           = 2
        cfg.cameraWidth    = CAM_W
        cfg.cameraHeight   = CAM_H
        cfg.resetCamera    = False
        cfg.scene          = SCENE
        for attr in ("cameraLinear", "cameraAngular"):
            v = getattr(cfg, attr)
            v.x = v.y = v.z = 0

        self.stub.SetConfiguration(cfg)
        cfg.resetRobot = False
        time.sleep(0.25)
        self.stub.SetConfiguration(cfg)

        req = google.protobuf.empty_pb2.Empty()

        while self.running:
            # ── Grab frame ───────────────────────────────────────────────────
            result    = self.stub.GetImageFrame(req)
            buf       = np.frombuffer(result.data, np.uint8)
            img_raw   = cv2.imdecode(buf, cv2.IMREAD_COLOR)

            if img_raw is None:
                time.sleep(self.timer_delta)
                continue

            frame = cv2.resize(img_raw, (OUT_W, OUT_H),
                               interpolation=cv2.INTER_LANCZOS4)
            self.cv_image = frame

            # ── Detect ───────────────────────────────────────────────────────
            annotated, sign = self.detector.detect_signs(frame.copy())

            # ── HUD overlay ──────────────────────────────────────────────────
            cv2.putText(annotated, f"Sign: {sign}", (10, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(annotated, f"t={self.running_time:.1f}s", (10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            cv2.imshow("Traffic Sign Vision", annotated)

            # ── Act ──────────────────────────────────────────────────────────
            self._decide_action(sign)

            # ── Tick ─────────────────────────────────────────────────────────
            if cv2.waitKey(1) & 0xFF == ord("q"):
                self.running = False
                break

            time.sleep(max(0, self.timer_delta - 0.001))
            self.running_time += self.timer_delta


def main():
    node   = SimRobotNode()
    thread = threading.Thread(target=node.callback, daemon=True)
    thread.start()

    try:
        while node.running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping …")
        node.running = False

    thread.join()
    cv2.destroyAllWindows()
    print("Node stopped safely.")


if __name__ == "__main__":
    main()
