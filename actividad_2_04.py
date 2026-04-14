import cv2
import numpy as np
import threading
import time

import grpc
import te3002b_pb2
import te3002b_pb2_grpc
import google.protobuf.empty_pb2

# --- YOUR LINE DETECTOR CLASS ---
class CenterLineDetector:
    def __init__(self):
        self.cameraWidth = 320
        self.cameraHeight = 240

    def detect_center_line(self, image):
        h, w = image.shape[:2]

        # ── 1. Levantar la mirada: Recortar a la MITAD inferior en vez de 1/4 ──
        y_start = h // 2 
        roi = image[y_start:h, 0:w]
 
        # ── 2. Convertir a escala de grises y suavizar ──
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 2)
 
        # ── 3. EL ARREGLO MÁGICO: THRESH_BINARY_INV ──
        # Esto hace que la línea negra se vuelva BLANCA (para que la vea findContours)
        # y que el piso claro se vuelva NEGRO (para ignorarlo).
        _, binary_otsu = cv2.threshold(
            blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
 
        # ── 4. Buscar candidatos ──
        best_candidate = self._find_best_candidate(binary_otsu, w, y_start)
 
        if best_candidate is None:
            # Fallback 1: Por si acaso la iluminación cambia y la línea es más clara
            binary_normal = cv2.bitwise_not(binary_otsu)
            best_candidate = self._find_best_candidate(binary_normal, w, y_start)
 
        if best_candidate is None:
            # Fallback 2: usar binarización HSV para detectar línea gris/blanca 
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            lower = np.array([0, 0, 180])
            upper = np.array([180, 50, 255])
            mask_white = cv2.inRange(hsv, lower, upper)
            best_candidate = self._find_best_candidate(mask_white, w, y_start)
 
        if best_candidate is None:
            # Fallback final: centro inferior de la imagen
            best_candidate = (w // 2, y_start + (h - y_start) // 2)
 
        return best_candidate

    def _find_best_candidate(self, binary_mask, img_width, y_offset, min_area=150):
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        cx_img_center = img_width / 2.0
        best = None
        best_dist = float("inf")

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue

            M = cv2.moments(cnt)
            if M["m00"] == 0:
                continue

            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])

            dist = abs(cx - cx_img_center)
            if dist < best_dist:
                best_dist = dist
                best = (cx, cy + y_offset)

        return best
# --------------------------------

class SimRobotNode():
    def __init__(self):
        self._addr="127.0.0.1"
        self.channel=grpc.insecure_channel(self._addr+':7072')
        self.stub = te3002b_pb2_grpc.TE3002BSimStub(self.channel)

        self.cv_image = None 
        self.result=None
        self.datacmd=te3002b_pb2.CommandData()
        self.dataconfig=te3002b_pb2.ConfigurationData()
        self.twist=[0,0,0,0,0,0]
        self.running = True
        self.timer_delta=0.025
        self.running_time=0.0
        
        # Instantiate your detector
        self.detector = CenterLineDetector()

    def callback(self):
        self.dataconfig.resetRobot = True
        self.dataconfig.mode = 2
        self.dataconfig.cameraWidth = 360
        self.dataconfig.cameraHeight = 240
        self.dataconfig.resetCamera = False
        self.dataconfig.scene = 2026
        self.dataconfig.cameraLinear.x = 0
        self.dataconfig.cameraLinear.y = 0
        self.dataconfig.cameraLinear.z = 0
        self.dataconfig.cameraAngular.x  = 0
        self.dataconfig.cameraAngular.y  = 0
        self.dataconfig.cameraAngular.z  = 0
        req=google.protobuf.empty_pb2.Empty()
        self.twist=[0.0,0.0,0.0,0.0,0.0,0]
        res=self.stub.SetConfiguration(self.dataconfig)
        self.dataconfig.resetRobot = False
        time.sleep(0.25)
        res=self.stub.SetConfiguration(self.dataconfig)

        while self.running:
            self.result = self.stub.GetImageFrame(req)
            img_buffer=np.frombuffer(self.result.data, np.uint8)
            img_in=cv2.imdecode(img_buffer, cv2.IMREAD_COLOR)
            img = img_in
            if img_in is not None:
                img=self.add_noise_to_image(img_in, 3)

            # Resize the image
            new_width = 320
            new_height = 240
            new_dim = (new_width, new_height)
            self.cv_image = cv2.resize(img, new_dim, interpolation=cv2.INTER_LANCZOS4)
 
            # --- VISION & CONTROL LOGIC ---
            # 1. Detect the line
            best_candidate = self.detector.detect_center_line(self.cv_image)
            
            # Variables for movement (Linear X is forward speed, Angular Z is turning)
            speed = 0.02
            turn = 0.0

            if best_candidate is not None:
                cx, cy = best_candidate
                
                # Draw a red dot on the image so we can see what the code is tracking
                cv2.circle(self.cv_image, (int(cx), int(cy)), 5, (0, 0, 255), -1)

                # 2. Proportional Control
                # Calculate the error (difference between center of screen and line)
                center_of_screen = new_width / 2.0
                error = center_of_screen - cx
                
                # Tuning parameter (Kp) - How aggressively it turns
                kp = 0.005
                turn = error * kp

            # Apply commands: [LinearX, LinearY, LinearZ, AngularX, AngularY, AngularZ]
            self.twist = [speed, 0.0, 0.0, 0.0, 0.0, turn]
            # ------------------------------

            self.datacmd.linear.x=self.twist[0]
            self.datacmd.linear.y=self.twist[1]
            self.datacmd.linear.z=self.twist[2]
            self.datacmd.angular.x=self.twist[3]
            self.datacmd.angular.y=self.twist[4]
            self.datacmd.angular.z=self.twist[5]
            self.result=self.stub.SetCommand(self.datacmd)

            cv2.imshow('Synthetic Image', self.cv_image)
            cv2.waitKey(1)
            time.sleep(self.timer_delta-0.001)
            self.running_time=self.running_time+self.timer_delta

    def add_noise_to_image(self,image, kernel_s, noise_level=5):
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

def main(args=None):
    robot_node = SimRobotNode()
    thread = threading.Thread(target=robot_node.callback)
    thread.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping the thread...")
        robot_node.running = False
        thread.join()
        cv2.destroyAllWindows()
        print("Thread stopped")

if __name__ == "__main__":
    main()