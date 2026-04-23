"""
capture_dataset.py — Capture training images directly from the simulator.
 
Usage:
    python capture_dataset.py --class Stop --split train
 
Controls (OpenCV window must be focused):
    SPACE  -> save current frame
    Q      -> quit
 
Images are saved as:
    dataset/images/<split>/<class>_<timestamp>.jpg
"""
 
import argparse
import time
from pathlib import Path
 
import cv2
import numpy as np
import grpc
import google.protobuf.empty_pb2
 
import te3002b_pb2
import te3002b_pb2_grpc
 
GRPC_ADDR    = "127.0.0.1:7072"
CAM_W, CAM_H = 360, 240
OUT_W, OUT_H = 320, 240
SCENE        = 2026
 
 
def add_noise_to_image(image, kernel_s, noise_level=5):
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv_image)
    noise = np.random.randint(-noise_level, noise_level + 1, v.shape, dtype='int16')
    v_noisy = v.astype('int16') + noise
    v_noisy = np.clip(v_noisy, 0, 255).astype('uint8')
    hsv_noisy = cv2.merge([h, s, v_noisy])
    noisy_image = cv2.cvtColor(hsv_noisy, cv2.COLOR_HSV2BGR)
    noisy_image = cv2.GaussianBlur(noisy_image, (kernel_s, kernel_s), 0)
    alpha = 0.55
    beta = 55
    output_image = cv2.convertScaleAbs(noisy_image, alpha=alpha, beta=beta)
    return output_image
 
 
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--class", dest="cls",
                   required=True,
                   choices=["Stop", "Workers", "Go_Straight", "Turn_Left_Right"],
                   help="Class label for captured images")
    p.add_argument("--split", dest="split",
                   default="train", choices=["train", "val"],
                   help="Dataset split to save into")
    return p.parse_args()
 
 
def main():
    args = parse_args()
    save_dir = Path("dataset/images") / args.split
    save_dir.mkdir(parents=True, exist_ok=True)
 
    channel = grpc.insecure_channel(GRPC_ADDR)
    stub    = te3002b_pb2_grpc.TE3002BSimStub(channel)
 
    # --- Mirror exactly what the working node does ---
    cfg = te3002b_pb2.ConfigurationData()
    cfg.resetRobot   = True
    cfg.mode         = 2
    cfg.cameraWidth  = CAM_W
    cfg.cameraHeight = CAM_H
    cfg.resetCamera  = False
    cfg.scene        = SCENE
    cfg.cameraLinear.x  = 0
    cfg.cameraLinear.y  = 0
    cfg.cameraLinear.z  = 0
    cfg.cameraAngular.x = 0
    cfg.cameraAngular.y = 0
    cfg.cameraAngular.z = 0
 
    stub.SetConfiguration(cfg)      # first call: reset
    cfg.resetRobot = False
    time.sleep(0.25)
    stub.SetConfiguration(cfg)      # second call: apply settings
 
    req   = google.protobuf.empty_pb2.Empty()
    count = 0
 
    print(f"Capturing for class '{args.cls}' -> {save_dir}")
    print("SPACE = save frame | Q = quit")
 
    while True:
        result  = stub.GetImageFrame(req)
        buf     = np.frombuffer(result.data, np.uint8)
        img_raw = cv2.imdecode(buf, cv2.IMREAD_COLOR)
 
        if img_raw is None:
            continue
 
        img = add_noise_to_image(img_raw, 3)
        frame = cv2.resize(img, (OUT_W, OUT_H), interpolation=cv2.INTER_LANCZOS4)
 
        display = frame.copy()
        cv2.putText(display, f"Class: {args.cls} | Saved: {count}",
                    (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(display, "SPACE=save  Q=quit",
                    (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.imshow("Dataset Capture", display)
 
        key = cv2.waitKey(1) & 0xFF
        if key == ord(" "):
            fname = save_dir / f"{args.cls}_{int(time.time()*1000)}.jpg"
            cv2.imwrite(str(fname), frame)
            count += 1
            print(f"  Saved {fname}")
        elif key == ord("q"):
            break
 
    cv2.destroyAllWindows()
    print(f"\nDone. {count} images saved to {save_dir}")
 
 
if __name__ == "__main__":
    main()