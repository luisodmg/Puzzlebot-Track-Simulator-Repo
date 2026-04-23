"""
train.py — Fine-tune YOLOv8 on your 4 traffic sign classes.

Run:
    python train.py

After training, the best weights will be saved to:
    runs/detect/traffic_signs/weights/best.pt
Copy that file to the weights/ folder and update detector.py.
"""

from ultralytics import YOLO

# ── Config ────────────────────────────────────────────────────────────────────
DATA_YAML   = "dataset.yaml"
BASE_MODEL  = "yolov8n.pt"   # nano = fastest; swap for yolov8s.pt if accuracy is low
EPOCHS      = 50             # increase to 100 once your dataset is larger
IMG_SIZE    = 320            # matches 320×240 camera feed
BATCH_SIZE  = 16             # lower to 8 if you run out of VRAM
PROJECT     = "runs/detect"
RUN_NAME    = "traffic_signs"
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("Loading base model …")
    model = YOLO(BASE_MODEL)

    print(f"Training for {EPOCHS} epochs …")
    model.train(
        data=DATA_YAML,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        project=PROJECT,
        name=RUN_NAME,
        exist_ok=True,        # overwrite previous run with same name
        pretrained=True,      # use COCO weights as starting point (transfer learning)
        optimizer="auto",
        patience=15,          # early-stop if no improvement for 15 epochs
        cache=True,           # cache images in RAM for faster training
        verbose=True,
    )

    best = f"{PROJECT}/{RUN_NAME}/weights/best.pt"
    print(f"\n✅ Training complete. Best weights saved to: {best}")
    print("Next step: copy that file to weights/ and set WEIGHTS_PATH in detector.py")


if __name__ == "__main__":
    main()
