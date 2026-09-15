import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import sounddevice as sd
import soundfile as sf
import time
import os

class SpeakerNode(Node):
    def __init__(self):
        super().__init__('speaker_node')
        self.last_audio_path = None

        self.subscription = self.create_subscription(
            String,
            '/emotion_sound',
            self.listener_callback,
            10)

        self.repeat_sub = self.create_subscription(
            String,
            '/repeat_sound',
            self.repeat_callback,
            10)

        self.get_logger().info('SpeakerNode ready. Waiting...')

    def listener_callback(self, msg):
        audio_path = msg.data.replace('New sound saved to: ', '').strip()
        if not os.path.exists(audio_path):
            self.get_logger().error(f"File does not exist: {audio_path}")
            return

        self.last_audio_path = audio_path
        self.get_logger().info(f'Playing new audio: {audio_path}')
        self.play_audio(audio_path)

    def repeat_callback(self, msg):
        if self.last_audio_path:
            self.get_logger().info(f'Repeating audio: {self.last_audio_path}')
            self.play_audio(self.last_audio_path)
        else:
            self.get_logger().warn('No audio to repeat.')

    def play_audio(self, path):
        try:
            data, fs = sf.read(path, dtype='float32')
            channels = data.shape[1] if data.ndim > 1 else 1

            time.sleep(0.1)

            with sd.OutputStream(samplerate=fs, channels=channels) as stream:
                stream.write(data)

            self.get_logger().info('Playback finished.')
        except Exception as e:
            self.get_logger().error(f'Failed to play audio: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = SpeakerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
