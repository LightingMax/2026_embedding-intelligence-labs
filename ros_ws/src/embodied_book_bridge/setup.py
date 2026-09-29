from setuptools import find_packages, setup

package_name = "embodied_book_bridge"

setup(
    name=package_name,
    version="0.2.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="LightingMax",
    maintainer_email="871772700@qq.com",
    description="Publish textbook scenario interfaces over ROS 2.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "scenario_publisher = embodied_book_bridge.scenario_publisher:main",
            "integration_demo = embodied_book_bridge.integration_demo:main",
        ]
    },
)
