from setuptools import setup, find_packages
with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")
setup(
    name="prajavani_grs",
    version="1.0.0",
    description="Decentralised Grievance Redressal System for Indian State Governments",
    author="Open Source Contributors",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
