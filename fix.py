import os
import subprocess

# 1. Create the content for pyproject.toml
pyproject_content = """[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build-meta"

[project]
name = "hospitrl"
version = "1.0.0"
description = "Hospital Resource Allocation Environment"
dependencies = [
    "fastapi",
    "uvicorn",
    "requests",
    "pydantic",
    "openai",
    "huggingface_hub",
    "openenv",
    "openenv-core>=0.2.0",
    "gymnasium"
]

[project.scripts]
hospitrl-server = "server.app:main"

[tool.setuptools]
packages = ["server", "my_env_v4"]
"""

def run():
    print("--- Starting Final Fix ---")
    
    # Write the pyproject.toml file
    with open("pyproject.toml", "w") as f:
        f.write(pyproject_content)
    print("Created pyproject.toml")

    # Ensure server is a package
    if not os.path.exists("server/__init__.py"):
        open("server/__init__.py", "a").close()
        print("Created server/__init__.py")

    # Install the missing build tools
    print("--- Installing build tools ---")
    subprocess.run(["pip", "install", "setuptools", "wheel"])
    
    # Install the project locally
    print("--- Installing project locally ---")
    subprocess.run(["pip", "install", "-e", "."])

    print("\nDONE! Now run 'openenv validate'")

if __name__ == "__main__":
    run()