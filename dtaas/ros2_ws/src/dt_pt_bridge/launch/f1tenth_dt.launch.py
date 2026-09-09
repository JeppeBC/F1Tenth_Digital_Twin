"""Brings up the full F1Tenth DT stack in one shot inside the DTaaS container:
sim + RViz2 (f1tenth_gym_ros), the DT<->PT UDP bridge, and the benchmark
loggers. Mirrors the multi-terminal workflow in the repo's top-level
README.md, minus the keyboard teleop terminal (run that manually in the
noVNC desktop so it has terminal focus) and the /teleop->/drive relay,
which is only needed once teleop is running.

Usage:
    ros2 launch dt_pt_bridge f1tenth_dt.launch.py pt_host:=<car-ip>
"""
import os
from datetime import datetime

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    run_label = datetime.now().strftime('%Y%m%d_%H%M%S')
    default_data_dir = os.path.join('/workspace/f1tenth/data', run_label)

    pt_host_arg = DeclareLaunchArgument(
        'pt_host',
        description='IP address of the physical car (dt_pt_listener.py)',
    )
    pt_port_arg = DeclareLaunchArgument('pt_port', default_value='9870')
    odom_port_arg = DeclareLaunchArgument('odom_port', default_value='9871')
    max_send_hz_arg = DeclareLaunchArgument('max_send_hz', default_value='50')
    data_dir_arg = DeclareLaunchArgument(
        'data_dir', default_value=default_data_dir,
        description='Where latency/trajectory CSVs for this run are written',
    )

    gym_bridge_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('f1tenth_gym_ros'),
                'launch', 'gym_bridge_launch.py',
            )
        )
    )

    teleop_relay = Node(
        package='topic_tools', executable='relay', name='teleop_to_drive',
        arguments=['/teleop', '/drive'], output='screen',
    )

    dt_pt_bridge = Node(
        package='dt_pt_bridge', executable='dt_pt_bridge', name='dt_pt_bridge',
        output='screen',
        parameters=[{
            'pt_host': LaunchConfiguration('pt_host'),
            'pt_port': LaunchConfiguration('pt_port'),
            'max_send_hz': LaunchConfiguration('max_send_hz'),
        }],
    )

    pt_odom_receiver = Node(
        package='dt_pt_bridge', executable='pt_odom_receiver',
        name='pt_odom_receiver', output='screen',
        parameters=[{'listen_port': LaunchConfiguration('odom_port')}],
    )

    latency_logger = Node(
        package='dt_pt_bridge', executable='latency_logger',
        name='latency_logger', output='screen',
        parameters=[{
            'output_dir': [LaunchConfiguration('data_dir'), '/latency']
        }],
    )

    trajectory_logger = Node(
        package='dt_pt_bridge', executable='trajectory_logger',
        name='trajectory_logger', output='screen',
        parameters=[{
            'output_dir': [LaunchConfiguration('data_dir'), '/trajectory'],
            'run_label': run_label,
        }],
    )

    return LaunchDescription([
        pt_host_arg, pt_port_arg, odom_port_arg, max_send_hz_arg, data_dir_arg,
        gym_bridge_launch,
        teleop_relay,
        dt_pt_bridge,
        pt_odom_receiver,
        latency_logger,
        trajectory_logger,
    ])
