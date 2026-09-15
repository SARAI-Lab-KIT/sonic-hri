from setuptools import setup
import os
from glob import glob

package_name = 'emotion_state'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'srv'), glob('srv/*.srv')),
    ],
    install_requires=[
        'setuptools',
        'rclpy',
        'emotion_msgs',
        'rosidl_default_generators',
    ],
    zip_safe=True,
    maintainer='Vlatka Tolj',
    maintainer_email='vlatka.tolj@student.kit.edu',
    description='Nodes for selecting and publishing target emotions in VA space.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'emotion_publisher = emotion_state.emotion_publisher:main',
            'emotion_controller = emotion_state.emotion_controller:main',
        ],
    },
)
