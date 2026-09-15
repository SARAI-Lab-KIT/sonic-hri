import rclpy
from rclpy.node import Node
from emotion_msgs.msg import EmotionState
from emotion_msgs.srv import SetEmotion
import pandas as pd
import numpy as np

VALENCE_MIN, VALENCE_MAX = -1.0, 1.0
AROUSAL_MIN, AROUSAL_MAX = -1.0, 1.0

def sample_uniform_region(center_v: float, center_a: float, radius: float):
    # sample (v,a) inside a given radius around (center_v, center_a)
    u = np.random.rand()
    r = np.sqrt(u) * radius    # uniform in area
    theta = 2.0 * np.pi * np.random.rand()
    v = center_v + r * np.cos(theta)
    a = center_a + r * np.sin(theta)
    v = float(np.clip(v, VALENCE_MIN, VALENCE_MAX))
    a = float(np.clip(a, AROUSAL_MIN, AROUSAL_MAX))
    return v, a

class EmotionPublisher(Node):
    def __init__(self):
        super().__init__('emotion_publisher')
        self.publisher_ = self.create_publisher(EmotionState, '/emotion_target', 10)

        EXCEL_PATH = '/home/vlatka_tolj/Desktop/Sonic_HRI/RER-Shared/Mikels_emotions.xlsx'

        df = pd.read_excel(EXCEL_PATH)
        self.emotions = {
            str(row['Emotion']).strip().lower(): (float(row['Valence']), float(row['Arousal']))
            for _, row in df.iterrows()
            if pd.notna(row['Emotion']) and pd.notna(row['Valence']) and pd.notna(row['Arousal'])
        }

        self.declare_parameter('radius', 0.10)
        self.declare_parameter('seed', None)

        seed = self.get_parameter('seed').value
        if seed is not None:
            np.random.seed(int(seed))
        # start with neutral emotion/intent
        self.current_emotion = 'neutral' if 'neutral' in self.emotions else next(iter(self.emotions.keys()))

        # sample VA near its center and publish
        self.srv = self.create_service(SetEmotion, 'set_emotion', self.set_emotion_callback)
        self.get_logger().info(
            "EmotionPublisher ready...\n"
            f"radius={self.get_parameter('radius').value}"
        )

        self.publish_sampled_emotion()

    def _sample_near_center(self, center_v, center_a):
        radius = float(self.get_parameter('radius').value)
        return sample_uniform_region(center_v, center_a, radius)

    def publish_sampled_emotion(self):
        center_v, center_a = self.emotions[self.current_emotion]
        v, a = self._sample_near_center(center_v, center_a)

        msg = EmotionState()
        msg.valence = v
        msg.arousal = a
        msg.source_folder = self.current_emotion

        self.publisher_.publish(msg)
        self.get_logger().info(
            f'Published "{self.current_emotion}": center=({center_v:.3f},{center_a:.3f}) '
            f'sampled=({v:.3f},{a:.3f})'
        )

    def set_emotion_callback(self, request, response):
        name = request.name.strip().lower()
        if name in self.emotions:
            self.current_emotion = name
            self.publish_sampled_emotion()
            response.success = True
            response.message = f"Emotion set to '{name}' and sampled target published."
        else:
            response.success = False
            response.message = f"Emotion '{name}' not found."
            self.get_logger().warn(response.message)
        return response

def main(args=None):
    rclpy.init(args=args)
    node = EmotionPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
