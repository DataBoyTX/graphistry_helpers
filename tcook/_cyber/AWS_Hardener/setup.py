"""Setup script for cloud-seer."""

from setuptools import setup, find_packages

setup(
    name="cloud-seer",
    version="0.1.0",
    description="Multi-cloud security audit tool with KPI reporting",
    author="Your Name",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "cloud_seer.reports.html": ["templates/*.html"],
    },
    install_requires=[
        "boto3>=1.34",
        "click>=8.0",
        "rich>=13.0",
        "jinja2>=3.0",
        "pyyaml>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "cloud-seer=cloud_seer.cli:main",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Security",
    ],
)
