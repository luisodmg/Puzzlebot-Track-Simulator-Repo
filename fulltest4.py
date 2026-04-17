import cv2
import numpy as np
import threading
import time

import grpc
import te3002b_pb2
import te3002b_pb2_grpc
import google.protobuf.empty_pb2

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
        
        self.detector = CenterLineDetector()
        self.frame_counter = 0

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
        self.stub.SetConfiguration(self.dataconfig)
        self.dataconfig.resetRobot = False
        time.sleep(0.25)
        self.stub.SetConfiguration(self.dataconfig)

        while self.running:
            self.result = self.stub.GetImageFrame(req)
            img_buffer=np.frombuffer(self.result.data, np.uint8)
            img_in=cv2.imdecode(img_buffer, cv2.IMREAD_COLOR)
            
            if img_in is not None:
                img=self.add_noise_to_image(img_in, 3)
            else:
                img = img_in

            new_width = 320
            new_height = 240
            new_dim = (new_width, new_height)
            self.cv_image = cv2.resize(img, new_dim, interpolation=cv2.INTER_LANCZOS4)
 
            # --- VISION & CONTROL LOGIC ---
            best_candidate = self.detector.detect_center_line(self.cv_image)
            
            # Velocidad recuperada a un valor funcional
            speed = 0.025
            turn = 0.0

            if best_candidate is not None:
                cx, cy = best_candidate
                angle = 0.0

                # --- LOGGER DE COLOR ---
                self.frame_counter += 1
                if self.frame_counter % 20 == 0:  
                    y_int, x_int = int(cy), int(cx)
                    if 0 <= y_int < self.cv_image.shape[0] and 0 <= x_int < self.cv_image.shape[1]:
                        pixel_bgr = self.cv_image[y_int, x_int]
                        pixel_hsv = cv2.cvtColor(np.uint8([[pixel_bgr]]), cv2.COLOR_BGR2HSV)[0][0]
                        print(f"\n--- LOGGER DE COLOR ---")
                        print(f"BGR: {pixel_bgr} | HSV: {pixel_hsv}")
                        print(f"-----------------------\n")

                # Dibujar objetivo
                cv2.circle(self.cv_image, (int(cx), int(cy)), 5, (0, 0, 255), -1)

                # Control Proporcional
                center_of_screen = new_width / 2.0
                error = center_of_screen - cx
                kp = 0.005 # Kp ajustado para evitar oscilaciones violentas
                turn = error * kp

            # Enviar comandos
            self.twist = [speed, 0.0, 0.0, 0.0, 0.0, turn]
            self.datacmd.linear.x=self.twist[0]
            self.datacmd.linear.y=self.twist[1]
            self.datacmd.linear.z=self.twist[2]
            self.datacmd.angular.x=self.twist[3]
            self.datacmd.angular.y=self.twist[4]
            self.datacmd.angular.z=self.twist[5]
            self.stub.SetCommand(self.datacmd)

            # Mostrar vista principal
            cv2.imshow('Synthetic Image', self.cv_image)
            
            # Mostrar la MÁSCARA REAL de Otsu
            if self.detector.debug_mask is not None:
                cv2.imshow('Mascara Otsu (Robot Vision)', self.detector.debug_mask)

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
        print("Deteniendo el nodo...")
        robot_node.running = False
        thread.join()
        cv2.destroyAllWindows()
        print("Nodo detenido de forma segura.")

if __name__ == "__main__":
    main()