import rclpy
from rclpy.node import Node
from emotion_msgs.srv import SetEmotion
from std_msgs.msg import String

class EmotionController(Node):
    def __init__(self):
        super().__init__('emotion_controller')

        self.cli = self.create_client(SetEmotion, '/set_emotion')
        self.repeat_pub = self.create_publisher(String, '/repeat_sound', 10)

        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for /set_emotion service...')

        self.get_logger().info('EmotionController ready.')

    def send_emotion(self, emotion_name: str):
        req = SetEmotion.Request()
        req.name = emotion_name.strip().lower()
        future = self.cli.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        response = future.result()
        if response.success:
            print(f"Sound for emotion {emotion_name}")
        else:
            print(f"{response.message}")

    def repeat_last_sound(self):
        msg = String()
        msg.data = 'repeat'
        self.repeat_pub.publish(msg)
        print("Repeat sent")

def main():
    rclpy.init()
    node = EmotionController()

    print("\nEmotion Controller")
    print("Type target emotion,")
    print(" type 'r' to repeat, or 'q' to quit\n")

    try:
        while True:
            key = input("Target: ").strip().lower()
            if key == 'q':
                print("Exiting.")
                break
            elif key == 'r':
                node.repeat_last_sound()
            elif key:
                node.send_emotion(key)
            else:
                print("Please type something.")
    except KeyboardInterrupt:
        print("\nExiting.")

    rclpy.shutdown()

if __name__ == '__main__':
    main()
