FROM ros:jazzy-ros-base

RUN bash -lc 'source /opt/ros/jazzy/setup.bash \
    && command -v colcon \
    && python3 -c "import rclpy; from std_msgs.msg import String"'
