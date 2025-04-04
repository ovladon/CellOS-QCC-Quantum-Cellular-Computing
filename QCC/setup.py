from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="qcc",
    version="0.1.0",
    author="QCC Team",
    author_email="info@qcc-project.org",
    description="Quantum Cellular Computing framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ovladon/QCC",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "fastapi>=0.95.0",
        "uvicorn>=0.22.0",
        "pydantic>=2.0.0",
        "websockets>=11.0.0",
        "aiohttp>=3.8.4",
        "PyYAML>=6.0",
        "jinja2>=3.1.2",
        "httpx>=0.24.0",
        "cryptography>=40.0.0",
        "pyjwt>=2.6.0",
        "bcrypt>=4.0.0",
        "passlib>=1.7.4",
        "qiskit>=0.42.0",
        "pyOpenSSL>=23.0.0",
        "web3>=6.0.0",
        "eth-typing>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.3.1",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.3.0",
            "mypy>=1.3.0",
            "flake8>=6.0.0",
        ],
        "docs": [
            "sphinx>=6.2.0",
            "sphinx-rtd-theme>=1.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "qcc=qcc.cli:main",
        ],
    },
)
