import time
import sys
import math
import numpy as np
import cv2

class TrafficLightDetection:
    def __init__(self):
        self.cameraWidth = 320
        self.cameraHeight = 240

    def detect_state(self, image):
        h, w = image.shape[:2]
        mitad_ancho = w // 2
        
        roi = image[:, 0:mitad_ancho]

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)


        lower_red1 = np.array([0, 70, 70])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 70, 70])
        upper_red2 = np.array([180, 255, 255])

        lower_yellow = np.array([15, 70, 70])
        upper_yellow = np.array([35, 255, 255])

        lower_green = np.array([40, 70, 70])
        upper_green = np.array([90, 255, 255])


        mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask_red = cv2.add(mask_red1, mask_red2)

        mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
        mask_green = cv2.inRange(hsv, lower_green, upper_green)

        def get_max_area(mask):
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return 0
            return max(cv2.contourArea(c) for c in contours)

        area_red = get_max_area(mask_red)
        area_yellow = get_max_area(mask_yellow)
        area_green = get_max_area(mask_green)

        state = "none"
        max_area = max(area_red, area_yellow, area_green)
        min_area = 30

        if max_area > min_area:
            if max_area == area_red:
                state = "red"
            elif max_area == area_yellow:
                state = "yellow"
            elif max_area == area_green:
                state = "green"

        return state