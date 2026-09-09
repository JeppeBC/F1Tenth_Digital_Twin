from setuptools import setup

package_name = 'dt_pt_bridge'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/f1tenth_dt.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='F1Tenth DTaaS',
    maintainer_email='bangshaab2411@gmail.com',
    description=(
        'DTaaS packaging of the F1Tenth DT<->PT bridge, benchmarking and '
        'teleop nodes.'
    ),
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'dt_pt_bridge = dt_pt_bridge.dt_pt_bridge:main',
            'dt_pt_listener = dt_pt_bridge.dt_pt_listener:main',
            'pt_odom_receiver = dt_pt_bridge.pt_odom_receiver:main',
            'latency_logger = dt_pt_bridge.latency_logger:main',
            'trajectory_logger = dt_pt_bridge.trajectory_logger:main',
            'ackermann_keyboard_teleop = '
            'dt_pt_bridge.ackermann_keyboard_teleop:main',
        ],
    },
)
