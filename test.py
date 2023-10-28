# %%
import openai
import random

def base_msg(robot, player_num):
    return f'''You are playing mafia, a party game with one hacker and 4 robots for a total of 5 robots.
Every night the hacker will choose a robot to kill. A hacked robot is no longer able to participate in the discussion.
In the morning the robots including the hacker converse in an attempt to reveal who the hacker is. This is followed with a vote on who to remove from the village.
The hacker loses if they are voted out of the game and wins if there is only one robot left.
You are {'a robot' if robot else 'the hacker'}.
You are player number {player_num}.
'''

class Agent:
    def __init__(self, hacker, player_num):
        self.hacker = hacker
        self.player_num = player_num
        self.context = ""
        
    def on_night(self):
        if not self.hacker:
            return
        prompt = "It is now nighttime. Choose a robot to hack."
    
    def on_day(self):
        prompt = "It is now daytime, begin discussing amongst the other 4 players who you suspect is the hacker. Keep reponses to 150 words."
    
    def request(prompt):
        openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": ""},
                {"role": "user", "content": "Who won the world series in 2020?"},
                {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
                {"role": "user", "content": "Where was it played?"}
            ]
        )
        
hacker = random.sample([1, 2, 3, 4, 5])
other = [Agent(hacker != i, i) for i in range(1, 6)]

