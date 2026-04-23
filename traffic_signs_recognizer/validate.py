"""
validate.py — Evaluate your trained model on the validation set.

Run AFTER training:
    python validate.py

Prints mAP50, mAP50-95, precision and recall per class.
"""

from ultralytics import YOLO

WEIGHTS_PATH = "weights/best.pt"   # update path if needed
DATA_YAML    = "dataset.yaml"
IMG_SIZE     = 320


def main():
    print(f"Loading weights from {WEIGHTS_PATH} …")
    model = YOLO(WEIGHTS_PATH)

    metrics = model.val(
        data=DATA_YAML,
        imgsz=IMG_SIZE,
        verbose=True,
    )

    print("\n── Results ──────────────────────────────")
    print(f"mAP50:     {metrics.box.map50:.4f}")
    print(f"mAP50-95:  {metrics.box.map:.4f}")
    print(f"Precision: {metrics.box.mp:.4f}")
    print(f"Recall:    {metrics.box.mr:.4f}")
    print("─────────────────────────────────────────")


if __name__ == "__main__":
    main()
