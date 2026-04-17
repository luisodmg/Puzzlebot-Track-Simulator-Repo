import cv2
import numpy as np

class CenterLineDetector:
    def __init__(self):
        self.cameraWidth = 320
        self.cameraHeight = 240
        self.debug_mask = None
        self.last_center = (self.cameraWidth // 2, int(self.cameraHeight * 0.875))
        self.max_jump_distance = 75  
        self.lower_color = np.array([20, 100, 100])
        self.upper_color = np.array([40, 255, 255])

    def detect_center_line(self, image):
        h, w = image.shape[:2]

        y_start = int(h * 0.75) 
        x_start = int(w * 0.25) 
        x_end = int(w * 0.75)   
        roi = image[y_start:h, x_start:x_end]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 1.4)
        _, mask = cv2.threshold(
            blurred, 0, 255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        kernel = np.ones((5, 5), np.uint8) 
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        self.debug_mask = mask

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        best_candidate = None
        best_score = float('inf')
        cx_screen_center = w / 2.0

        for c in contours:
            area = cv2.contourArea(c)
            
            if area < 250: 
                continue

            _, _, _, h_box = cv2.boundingRect(c)
            if h_box < 15:
                continue

            moments = cv2.moments(c)
            if moments["m00"] == 0:
                continue

            cx = int(moments["m10"] / moments["m00"]) + x_start
            cy = int(moments["m01"] / moments["m00"]) + y_start

            dist_to_center = abs(cx - cx_screen_center)
            dist_to_last = ((cx - self.last_center[0])**2 + (cy - self.last_center[1])**2)**0.5

            if dist_to_last > self.max_jump_distance:
                continue

            score = (dist_to_center * 0.2) + (dist_to_last * 0.8)

            if score < best_score:
                best_score = score
                best_candidate = (cx, cy)

        if best_candidate is not None:
            self.last_center = best_candidate
            return self.last_center
        else:        
            return None