import rclpy
from rclpy.node import Node
from emotion_msgs.msg import EmotionState
import pandas as pd
import numpy as np
import os

EXCEL_PATH = "/home/vlatka_tolj/Desktop/Sonic_HRI/RER-Shared/Bleep/Data_Labelling.xlsx"

class ClosestEmotionDetection(Node):
    def __init__(self):
        super().__init__('closest_emotion_detection')

        self.df = pd.read_excel(EXCEL_PATH)
        self.df = self.df.dropna(subset=['Valence', 'Arousal'])

        self.subscription = self.create_subscription(
            EmotionState,
            '/emotion_target',
            self.listener_callback,
            10)

        self.publisher_ = self.create_publisher(EmotionState, '/closest_emotion_detection', 10)

    def listener_callback(self, msg):
        valence = msg.valence
        arousal = msg.arousal
        self.get_logger().info(f"For valence={valence:.2f}, arousal={arousal:.2f}")

        # Euclidean distance in VA space
        diffs_v = self.df['Valence'].to_numpy() - valence
        diffs_a = self.df['Arousal'].to_numpy() - arousal
        dists = np.sqrt(diffs_v ** 2 + diffs_a ** 2)
        closest_idx = int(np.argmin(dists))

        closest_emotion = self.df.iloc[closest_idx]['Emotion / Intent']

        out_msg = EmotionState()
        out_msg.valence = valence
        out_msg.arousal = arousal
        out_msg.source_folder = str(closest_emotion)
        self.publisher_.publish(out_msg)

        self.get_logger().info(f"closest emotion/intent is: {closest_emotion}")


def main(args=None):
    rclpy.init(args=args)
    node = ClosestEmotionDetection()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
