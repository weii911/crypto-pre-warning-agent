# train_2025.py
import sqlite3
import pandas as pd
import gymnasium as gym
from gymnasium import spaces
import numpy as np
from stable_baselines3 import PPO
import config

class Crypto2025TrainingEnv(gym.Env):
    def __init__(self):
        super(Crypto2025TrainingEnv, self).__init__()
        conn = sqlite3.connect(config.DB_REAL)
        self.df = pd.read_sql_query("SELECT * FROM market_data_2025", conn)
        conn.close()
        
        self.current_step = 0
        self.max_steps = len(self.df) - 1
        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(5,), dtype=np.float32)
        
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        return self._get_obs(), {}
        
    def _get_obs(self):
        row = self.df.iloc[self.current_step]
        return np.array([row['oi_rate'], row['volume_pump'], row['price_position'], row['htf_price_position'], row['orderbook_delta']], dtype=np.float32)
        
    def step(self, action):
        row = self.df.iloc[self.current_step]
        reward = 0
        is_valuable_move = abs(row['price_change']) >= 0.012
        
        if action == 2:
            if is_valuable_move:
                reward = 200  # 抓到真正的大突破，給予獎賞
            else:
                reward = -80  # 價格沒拉開，在盤整區回報，處罰
        elif action == 0:
            if is_valuable_move:
                reward = -150 # 漏報真正的大波動，大罰
            else:
                reward = 15   # 橫盤雜訊成功過濾，給予獎賞
                
        self.current_step += 1
        done = self.current_step >= self.max_steps
        return self._get_obs(), reward, done, False, {}

if __name__ == "__main__":
    print("以2025 BTC數據訓練中")
    env = Crypto2025TrainingEnv()
    model = PPO("MlpPolicy", env, verbose=1, learning_rate=0.0003, n_steps=64)
    model.learn(total_timesteps=200000)
    model.save("best_crypto_agent")
    print("訓練完成 - best_crypto_agent.zip")