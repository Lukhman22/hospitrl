import os
from huggingface_hub import HfApi

def deploy():
    # We pull the token from the terminal's memory (environment variable)
    token = os.getenv("HF_TOKEN")
    
    if not token:
        print("❌ ERROR: HF_TOKEN not found in terminal memory.")
        print("Please run: export HF_TOKEN=your_token_here")
        return

    try:
        api = HfApi()
        repo_id = "lukhman22/hospitrl" 

        print(f"Step 1: Uploading project files to {repo_id}...")
        
        # Uploading without keeping the secret in the file
        api.upload_folder(
            folder_path=".",
            repo_id=repo_id,
            repo_type="space",
            token=token,
            ignore_patterns=["venv/*", ".git/*", "__pycache__/*"]
        )
        
        print("\n✅ SUCCESS: Project deployed to Hugging Face!")
        print(f"URL: https://huggingface.co/spaces/{repo_id}")

    except Exception as e:
        print(f"\n❌ DEPLOYMENT FAILED: {e}")

if __name__ == "__main__":
    deploy()