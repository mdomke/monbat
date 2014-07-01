from setuptools import setup, find_packages


setup(
    name="monbat",
    version="0.0.1",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "monbat = monbat:run"
        ]
    },
    install_requires=[
        "docopt",
        "progressbar2",
    ],
    extras_require={
        "plot": [
            "bokeh",
            "numpy"
        ]
    }
)
