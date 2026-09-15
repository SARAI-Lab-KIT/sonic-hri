cmake_minimum_required(VERSION 3.5)
project(emotion_state)

find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "srv/SetEmotion.srv"
)
