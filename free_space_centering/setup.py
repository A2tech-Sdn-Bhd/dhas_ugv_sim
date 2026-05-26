from setuptools import find_packages, setup

package_name = 'free_space_centering'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='your_name',
    maintainer_email='your@email.com',
    description='Free space centering using occupancy grid map',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'free_space_centering = free_space_centering.free_space_centering:main',
            'centering_cmd_mux = free_space_centering.centering_cmd_mux:main',
        ],
    },
)
