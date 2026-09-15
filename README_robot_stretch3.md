# Getting started

Maintainer(s): Victoria Yang (victoria.yang@kit.edu)

---
## 0. Setting up Stretch 3 robot

### 0.1 Power on and connect to Stretch 3
 Follow the instructions as described here: https://docs-arch.hello-robot.com/0.3/getting_started/connecting_to_stretch/ 

#### 0.1.1 When you are finished using Stretch 3
When you are finished using the robot, follow the shutoff instructions for the Stretch3 as described here: https://docs-arch.hello-robot.com/0.3/getting_started/hello_robot/#shutting-down-stretch 

### 0.2 Must run the following when you open new terminals and before you run each ros pacakge in section 3 of README_workspace_setup.md
The following commands source the ros environment, activate a virtual environment for the corresponding python requirements of the evolutionary strategy (ES), and source the executables for ros2 nodes

    source /opt/ros/humble/setup.bash
    source ~/sonic_hri_venv_ws/sonic-hri-venv/bin/activate
    export PYTHONNOUSERSITE=1
    source ~/sonic_hri_venv_ws/install/setup.bash

Then you can run the packages with the following command format (exact command detailed in section 3):
    ros2 run <ros_package_name> <ros_node_name>

#### 0.3 (optional) Volume settings
Command to check the sound level:

    amixer

Sondlevel output example:
~~~ini
    Simple mixer control 'PCM',0
    Capabilities: pvolume pswitch pswitch-joined
    Playback channels: Front Left - Front Right
    Limits: Playback 0 - 147
    Mono:
    Front Left: Playback 44 [30%] [-20.16dB] [on]
    Front Right: Playback 44 [30%] [-20.16dB] [on]
~~~

Adjust volume level using the following command template:

    amixer set PCM <volume percentage or a number 0-147>

Full volume example:

    amixer set PCM 100%

Save the volume setting to persist upon reboot: 

    sudo alsactl store
---