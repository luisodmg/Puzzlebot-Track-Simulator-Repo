import cv2
import numpy as np
import threading
import time

import grpc
import te3002b_pb2
import te3002b_pb2_grpc
import google.protobuf.empty_pb2

# Importamos YOLO de ultralytics
from ultralytics import YOLO

# --- NUEVA CLASE DEL DETECTOR DE SEÑALAMIENTOS (PIPELINE) ---
class TrafficSignDetection:
    def __init__(self):
        # 1. Cargar el modelo CNN (Acercamiento B)
        # Asegúrate de tener tu modelo entrenado en la misma carpeta
        self.model = YOLO('yolov8n.pt')
        
        # Clases que te pide la actividad
        self.class_names = ['Stop', 'Workers', 'Go Straight', 'Turn Left/Right']

    # 2. Métrica de Calidad de Imagen (Acercamiento A)
    def is_blurry(self, image, threshold=100.0):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        fm = cv2.Laplacian(gray, cv2.CV_64F).var()
        return fm < threshold

    def detect_signs(self, image):
        # Filtro de calidad de imagen
        if self.is_blurry(image):
            return image, "Borroso"

        # Detección con CNN
        results = self.model(image, conf=0.5, verbose=False)
        detected_sign = "None"

        # Dibujar las cajas sobre la imagen
        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_id = int(box.cls[0])
                
                # Proteger contra índices fuera de rango si el modelo detecta algo extra
                if cls_id < len(self.class_names):
                    detected_sign = self.class_names[cls_id]
                else:
                    detected_sign = f"Clase_desconocida_{cls_id}"

                # Dibujar bounding box y etiqueta
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(image, detected_sign, (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        return image, detected_sign


# --- NODO DEL ROBOT PARA EL SIMULADOR (RECICLADO Y ADAPTADO) ---
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
        
        # Instanciamos el nuevo detector de señales
        self.detector = TrafficSignDetection()

    def callback(self):
        self.dataconfig.resetRobot = True
        self.dataconfig.mode = 2
        self.dataconfig.cameraWidth = 360
        self.dataconfig.cameraHeight = 240
        self.dataconfig.resetCamera = False
        self.dataconfig.scene = 2026 # Revisa si hay una escena específica para las señales
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
                # Quitamos el ruido extra para no afectar a YOLO innecesariamente
                # o puedes dejarlo si tu modelo es muy robusto.
                img = img_in 
            else:
                img = img_in

            if img is not None:
                new_width = 320
                new_height = 240
                new_dim = (new_width, new_height)
                self.cv_image = cv2.resize(img, new_dim, interpolation=cv2.INTER_LANCZOS4)

                # --- NUEVA LÓGICA DE VISIÓN ---
                # Pasamos el frame por el detector de señales
                processed_image, current_sign = self.detector.detect_signs(self.cv_image)
                
                # Imprimimos el estado en la pantalla
                cv2.putText(processed_image, f"En frente: {current_sign}", (10, 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                # Mostrar vista principal con las cajas de YOLO dibujadas
                cv2.imshow('Traffic Sign Vision', processed_image)

            # Comandos de movimiento (puedes programar lógica para que se mueva 
            # dependiendo de la señal que detectó)
            self.twist = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            self.datacmd.linear.x=self.twist[0]
            self.datacmd.linear.y=self.twist[1]
            self.datacmd.linear.z=self.twist[2]
            self.datacmd.angular.x=self.twist[3]
            self.datacmd.angular.y=self.twist[4]
            self.datacmd.angular.z=self.twist[5]
            self.stub.SetCommand(self.datacmd)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.running = False
                break
                
            time.sleep(self.timer_delta-0.001)
            self.running_time=self.running_time+self.timer_delta

def main(args=None):
    robot_node = SimRobotNode()
    thread = threading.Thread(target=robot_node.callback)
    thread.start()
    try:
        while robot_node.running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Deteniendo el nodo...")
        robot_node.running = False
        
    thread.join()
    cv2.destroyAllWindows()
    print("Nodo detenido de forma segura.")

if __name__ == "__main__":
    main()