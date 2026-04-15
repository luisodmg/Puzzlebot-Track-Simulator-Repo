import cv2
import numpy as np

class CenterLineDetector:
    def __init__(self):
        self.cameraWidth = 320
        self.cameraHeight = 240
        self.debug_mask = None
        # Iniciamos la memoria asumiendo que el robot arranca alineado
        self.last_center = (self.cameraWidth // 2, int(self.cameraHeight * 0.875))

    def detect_center_line(self, image):
        h, w = image.shape[:2]

        # 1. REGLA ESTRICTA DE LA ACTIVIDAD: Utiliza sólo el 1/4 inferior
        # Esto ayuda a no ver las intersecciones hasta que estemos sobre ellas
        y_start = int(h * 0.75) 
        roi = image[y_start:h, :]

        # 2. Suavizado y Binarización (Otsu)
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 1.4)
        _, binary = cv2.threshold(
            blurred, 0, 255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        # Limpieza morfológica para quitar ruido
        kernel = np.ones((3, 3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        self.debug_mask = binary

        # 3. Detección de Contornos
        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        best_candidate = None
        best_score = float('inf')
        cx_screen_center = w / 2.0

        for c in contours:
            area = cv2.contourArea(c)
            
            # 🔥 FILTRO: Como la línea central es continua en el 1/4 inferior, 
            # tendrá un área grande. Ignoramos contornos pequeños (ruido o punteadas lejanas).
            if area < 80: 
                continue

            # 4. Cálculo del Centroide
            moments = cv2.moments(c)
            if moments["m00"] == 0:
                continue

            cx = int(moments["m10"] / moments["m00"])
            cy = int(moments["m01"] / moments["m00"]) + y_start

            # Calculamos qué tan lejos está del centro de la pantalla
            dist_to_center = abs(cx - cx_screen_center)
            
            # Calculamos qué tan lejos está del último punto conocido (inercia)
            dist_to_last = ((cx - self.last_center[0])**2 + (cy - self.last_center[1])**2)**0.5

            # 🔥 PUNTUACIÓN DE RASTREO: 
            # Le damos peso a que no brinque repentinamente (dist_to_last) 
            # y a que tienda a estar en el centro del carril (dist_to_center).
            score = (dist_to_center * 0.4) + (dist_to_last * 0.6)

            if score < best_score:
                best_score = score
                best_candidate = (cx, cy)

        # Si encontramos una línea válida, actualizamos la memoria
        if best_candidate is not None:
            self.last_center = best_candidate

        # Retornamos el mejor candidato (o el último conocido si hubo ruido extremo)
        return self.last_center