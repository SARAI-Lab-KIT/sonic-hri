from setuptools import find_packages, setup

package_name = 'emotion_speaker'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Vlatka Tolj',
    maintainer_email='vlatka.tolj@student.kit.edu',
    description='ROS2 node playing/repeating sounds.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'speaker_node = emotion_speaker.speaker_node:main',
        ],
    },
)
