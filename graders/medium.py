def grade(total_reward: float) -> float:
    score = total_reward * 0.9
    return float(max(0.0001, min(0.9999, score)))