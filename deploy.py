from huggingface_hub import HfApi, login
import os
HF_TOKEN = os.getenv("Hhf_ecrhnbSKBJIHkXSEdhkEEAKIKTCauHZzZg") 

try:
    print("Attempting to login...")
    login(token=HF_TOKEN.strip())
    print("Login successful!")
except Exception as e:
    print(f"Login failed: {e}")
    exit()

api = HfApi()
username = "lukhman22"
repo_id = f"{username}/hospitrl"

try:
    print(f"Creating/Checking Space: {repo_id}")
    api.create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="docker",
        private=False,
    )
except Exception as e:
    print(f"Note: Repository already exists or was verified.")

print("Uploading files to Hugging Face... this may take a minute.")
try:
    api.upload_folder(
        folder_path=".",
        repo_id=repo_id,
        repo_type="space",
        ignore_patterns=[
            "venv/*",
            "build/*",
            "*.egg-info/*",
            "__pycache__/*",
            ".git/*",
            "deploy.py",
            "*.pyc",
            ".DS_Store"
        ]
    )
    print(f"SUCCESS! View your space here: https://huggingface.co/spaces/{repo_id}")
except Exception as e:
    print(f"Upload failed: {e}")