import sqlite3
import pandas as pd
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import config

class CryptoAgentEnv(gym.Env):
    def __init__(self):
        super(CryptoAgentEnv, self).__init__()
        
        conn = sqlite3.connect(config.DB_REAL)
        self.df = pd.read_sql_query("SELECT * FROM market_data_2025", conn)
        conn.close()
        
        self.current_step = 0
        self.max_steps = len(self.df) - 1
        
        # 動作空間：0=裝死, 1=輕度監控, 2=喚醒LLM通報
        self.action_space = spaces.Discrete(3)
        
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(5,), dtype=np.float32
        )
        
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        return self._get_obs(), {}
        
    def _get_obs(self):
        row = self.df.iloc[self.current_step]
        return np.array([
            row['oi_rate'],
            row['volume_pump'],
            row['price_position'],
            row['htf_price_position'],
            row['orderbook_delta']
        ], dtype=np.float32)
        
    def step(self, action):
        row = self.df.iloc[self.current_step]
        reward = 0
        
        is_valuable_move = abs(row.get('price_change', 0.0)) >= 0.012
        if action == 2 and is_valuable_move:
            reward = 100
        elif action == 0 and not is_valuable_move:
            reward = 10
            
        self.current_step += 1
        done = self.current_step >= self.max_steps
        
        return self._get_obs(), reward, done, False, {}