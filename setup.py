from setuptools import setup

setup(
    name="taskmaster",
    version="0.1",
    py_modules=["taskmaster"],
    entry_points={
        "console_scripts": [
            "taskmaster=taskmaster:main",
        ],
    },
)
