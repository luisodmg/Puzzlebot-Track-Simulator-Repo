import cv2

import numpy as np

import threading

import time



import grpc

import te3002b_pb2

import te3002b_pb2_grpc

import google.protobuf.empty_pb2



# --- CLASE DEL DETECTOR DE SEMÁFORO ---

# --- CLASE DEL DETECTOR DE SEMÁFORO ---
class TrafficLightDetection:
    def __init__(self):
        self.cameraWidth = 320
        self.cameraHeight = 240

    def detect_state(self, image):
        # --- NUEVA LÓGICA DE RECORTE (ROI) ---
        # Obtenemos las dimensiones de la imagen que recibe el método
        h, w = image.shape[:2]
        mitad_ancho = w // 2
        
        # Recortamos la imagen para quedarnos solo con la mitad izquierda
        # Así ignoramos los carteles a la derecha
        roi = image[:, 0:mitad_ancho]

        # 1. Convertir a HSV (Asegúrate de procesar el 'roi', no la 'image' original)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # 2. Definir rangos
        lower_red1 = np.array([0, 70, 70])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 70, 70])
        upper_red2 = np.array([180, 255, 255])

        lower_yellow = np.array([15, 70, 70])
        upper_yellow = np.array([35, 255, 255])

        lower_green = np.array([40, 70, 70])
        upper_green = np.array([90, 255, 255])

        # 3. Máscaras
        mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask_red = cv2.add(mask_red1, mask_red2)

        mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
        mask_green = cv2.inRange(hsv, lower_green, upper_green)

        # 4. Encontrar el área más grande
        def get_max_area(mask):
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return 0
            return max(cv2.contourArea(c) for c in contours)

        area_red = get_max_area(mask_red)
        area_yellow = get_max_area(mask_yellow)
        area_green = get_max_area(mask_green)

        # 5. Lógica de estado
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



# --- NODO DEL ROBOT PARA EL SIMULADOR ---

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

       

        # Instanciamos nuestro nuevo detector

        self.detector = TrafficLightDetection()



    def callback(self):

        self.dataconfig.resetRobot = True

        self.dataconfig.mode = 2

        self.dataconfig.cameraWidth = 360

        self.dataconfig.cameraHeight = 240

        self.dataconfig.resetCamera = False

        self.dataconfig.scene = 2026 # Asegúrate de que esta sea la escena del semáforo

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

 

            # --- VISION LOGIC ---

            # Llamamos a nuestro detector de semáforos

            current_state = self.detector.detect_state(self.cv_image)

           

            # Imprimimos el estado en la consola y lo dibujamos en la pantalla

            # print(f"Estado del semáforo: {current_state}")

            cv2.putText(self.cv_image, f"ESTADO: {current_state.upper()}", (20, 40),

                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)



            # Enviar comandos (El robot se queda quieto mientras evalúa)

            self.twist = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

            self.datacmd.linear.x=self.twist[0]

            self.datacmd.linear.y=self.twist[1]

            self.datacmd.linear.z=self.twist[2]

            self.datacmd.angular.x=self.twist[3]

            self.datacmd.angular.y=self.twist[4]

            self.datacmd.angular.z=self.twist[5]

            self.stub.SetCommand(self.datacmd)



            # Mostrar vista principal

            cv2.imshow('Traffic Light Vision', self.cv_image)



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