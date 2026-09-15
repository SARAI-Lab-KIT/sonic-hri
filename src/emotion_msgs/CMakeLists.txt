cmake_minimum_required(VERSION 3.5)
project(emotion_msgs)

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(std_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# Generate messages
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/EmotionState.msg"
   "srv/SetEmotion.srv"
  DEPENDENCIES std_msgs
)

# Export message runtime
ament_export_dependencies(rosidl_default_runtime)

ament_package()
