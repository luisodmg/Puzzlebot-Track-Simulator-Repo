#Author: AECL

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy

import cv2
from cv_bridge import CvBridge
import numpy as np
import threading
import time

import grpc
import te3002b_pb2
import te3002b_pb2_grpc
import google.protobuf.empty_pb2

class SimRobotNode(Node):
    def __init__(self):
        super().__init__('gs_sim_robot_node')
        self._addr="127.0.0.1"
        self.channel=grpc.insecure_channel(self._addr+':7072')
        self.stub = te3002b_pb2_grpc.TE3002BSimStub(self.channel)
        qos_profile = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )
        self.cv_image = None 
        self.result=None
        self.twist=[0.0,0.0,0.0,0.0,0.0,0.0]
        self.datacmd=te3002b_pb2.CommandData()
        self.datacmd.linear.x=self.twist[0]
        self.datacmd.linear.y=self.twist[1]
        self.datacmd.linear.z=self.twist[2]
        self.datacmd.angular.x=self.twist[3]
        self.datacmd.angular.y=self.twist[4]
        self.datacmd.angular.z=self.twist[5]
        self.dataconfig=te3002b_pb2.ConfigurationData()
        self.dataconfig.resetRobot = True
        self.dataconfig.mode = 0
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
        self.running = True
        self.timer_delta=0.025
        self.running_time=0.0
        self.req=google.protobuf.empty_pb2.Empty()
        self.result=self.stub.SetConfiguration(self.dataconfig);
        self.dataconfig.resetRobot = False
        time.sleep(1)
        self.result=self.stub.SetConfiguration(self.dataconfig);

        self.bridge = CvBridge()
        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.listener_callback,
            qos_profile=qos_profile)
        self.publisher_ = self.create_publisher(Image, 'Image', 10)
        self.timer = self.create_timer(self.timer_delta, self.timer_callback)

    def listener_callback(self, msg):
        self.get_logger().info('Received Command')
        self.twist=[msg.linear.x,msg.linear.y,msg.linear.z,msg.angular.x, msg.angular.y, msg.angular.z]
        self.datacmd.linear.x=self.twist[0]
        self.datacmd.linear.y=self.twist[1]
        self.datacmd.linear.z=self.twist[2]
        self.datacmd.angular.x=self.twist[3]
        self.datacmd.angular.y=self.twist[4]
        self.datacmd.angular.z=self.twist[5]
        print("Twist: " + str(self.twist))

    def timer_callback(self):
        self.result = self.stub.GetImageFrame(self.req)
        print("Time:" + str(self.running_time))
        print("frame ID: " + str(self.result.seq))
        print("----")
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

        if self.cv_image is not None:
            self.publisher_.publish(self.bridge.cv2_to_imgmsg(np.array(self.cv_image), "bgr8"))
            self.get_logger().info('Publishing image')
        else:
            self.get_logger().info('No image')
        try:
            self.result=self.stub.SetCommand(self.datacmd)
        except:
            self.datacmd.linear.x=0
            self.datacmd.linear.y=0
            self.datacmd.linear.z=0
            self.datacmd.angular.x=0
            self.datacmd.angular.y=0
            self.datacmd.angular.z=0
            self.result=self.stub.SetCommand(self.datacmd)

        cv2.imshow('Synthetic Image', self.cv_image)
        cv2.waitKey(1)
        time.sleep(self.timer_delta-0.001)
        self.running_time=self.running_time+self.timer_delta

    def add_noise_to_image(self,image, kernel_s, noise_level=5):
        # Convert the BGR image to HSV color space
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Split the HSV image into its channels
        h, s, v = cv2.split(hsv_image)
        
        # Generate random noise to be added to the V channel
        noise = np.random.randint(-noise_level, noise_level + 1, v.shape, dtype='int16')

        # Add the noise to the V channel
        v_noisy = v.astype('int16') + noise

        # Clip the values to be in the valid range [0, 255]
        v_noisy = np.clip(v_noisy, 0, 255).astype('uint8')

        # Merge the channels back to form the noisy HSV image
        hsv_noisy = cv2.merge([h, s, v_noisy])
        
        # Convert the noisy HSV image back to BGR color space
        noisy_image = cv2.cvtColor(hsv_noisy, cv2.COLOR_HSV2BGR)

        noisy_image = cv2.GaussianBlur(noisy_image, (kernel_s, kernel_s), 0)
        
        # Adjust contrast and brightness
        alpha = 0.55   # Contrast (1.0 = original)
        beta = 55     # Brightness (0 = original)

        output_image = cv2.convertScaleAbs(noisy_image, alpha=alpha, beta=beta)

        return output_image

def main(args=None):
    rclpy.init(args=args)
    robot_node = SimRobotNode()
    rclpy.spin(robot_node)
    print("Stopping the thread...")
    robot_node.destroy_node()
    robot_node.c.close()
    rclpy.shutdown()
    cv2.destroyAllWindows()
    print("Thread stopped")

if __name__ == "__main__":
    main()