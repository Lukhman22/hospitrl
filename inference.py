import asyncio
import os
import json
from openai import OpenAI
from my_env_v4.env import HospitRL_Env
from my_env_v4.models import Action

client = OpenAI(
    base_url=os.getenv("API_BASE_URL", "https://api.openai.com/v1"),
    api_key=os.getenv("OPENAI_API_KEY", "no-key-provided")
)

async def main():
    env = HospitRL_Env()
    obs, info = env.reset()
    
    task_name = "ward_baseline"
    model_name = os.getenv("MODEL_NAME", "gpt-4")
    
    print(f"[START] task={task_name} env=hospitrl model={model_name}")
    
    rewards = []
    steps_taken = 0
    success = False

    try:
        for step in range(1, 11):
            steps_taken = step
            
            my_action = Action(
                source_ward=1, 
                target_ward=0, 
                staff_count=1
            )
            
            obs, reward, done, truncated, info = env.step(my_action)
            rewards.append(reward)
            
            print(f"[STEP] step={step} action=move_staff reward={reward} done={done} error=null")
            
            if done or truncated:
                break

        score = sum(rewards) / len(rewards) if rewards else 0.0
        score = max(0.0, min(1.0, score))
        success = score >= 0.5

    finally:
        print(f"[END] success={str(success).lower()} steps={steps_taken} score={score}")

if __name__ == "__main__":
    asyncio.run(main())