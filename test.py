# %%
import openai
import random
from tqdm.contrib.concurrent import thread_map
thread_map = map
from tqdm import tqdm
import re
import os
import json

from dotenv import load_dotenv
load_dotenv()
import time
import statistics

openai.api_key = "EMPTY" #os.getenv("OPENAI_API_KEY")
openai.api_base = "http://localhost:8000/v1"

models = openai.Model.list()
model = models["data"][0]["id"]

def base_msg(hacker, player_num):
    def find_accent():
        match player_num:
            case 1:
                return "Use an old english writing style."
            case 2:
                return "Use a southern writing style."
            case 3:
                return "Slurr your writing."
            case 4:
                return "Use figures of speech."
            case 5:
                return "Write with European English."
    
    return f'''You are playing mafia, a party game with one hacker and 4 robots for a total of 5 robots.
Every night the hacker will choose a robot to kill. A hacked robot is no longer able to participate in the discussion.
In the morning the robots including the hacker converse in an attempt to reveal who the hacker is. This is followed with a vote on who to remove from the village.
The hacker loses if they are voted out of the game and wins if there is only one robot left.
You are {'the hacker. Do your best not to reveal yourself!' if hacker else 'a robot'}.
You are player number {player_num}.
{find_accent()}
'''

def request(messages):
    failed = True
    while failed:
        failed = False
        try:
            #Make your OpenAI API request here
            response = openai.ChatCompletion.create(model=model, messages=messages, request_timeout=10, top_k=4, presence_penalty=0.6, temperature=1)
        except openai.error.APIError as e:
            #print(e)
            failed = True
        except openai.error.APIConnectionError as e:
            #print(e)
            failed = True
        except openai.error.RateLimitError as e:
            #print(e)
            time.sleep(2)
            failed = True
        except openai.error.Timeout as e:
            #print(e)
            time.sleep(2)
            failed = True
    return response['choices'][0]['message']['content']

class MessageManager:
    def __init__(self, hacker):
        self.prompts = []
        self.hacker = hacker
    
    def build_context(self, player):
        return [{"role": "system", "content": base_msg(player == self.hacker, player)}] \
            + [{"role": "user" if str(player) != str(i['role']) else 'assistant', "content": i['content']} for i in self.prompts]
        
    def add_context(self, player: int, response: str):
        self.prompts.append({"role": player, "content": response})
    
    def add_murder(self, murder_msg: int):
        self.prompts.append({"role": "system", "content": f"Player {hacked} has been hacked.\n"})
    
    def add_context_list(self, response: list[str]):
        # start player by 1
        #Player {i+1} said:\n{
        self.prompts.extend([{"role": i+1, "content": f'Player {i+1} said: {j}'} for i, j in enumerate(response)])
    
    def build_context_night(self):
        c = self.build_context(self.hacker)
        c.append({"role": "system", "content": "It is now nighttime. Choose a robot to hack by number. Choose wisely.\n"})
        return c
    
    def build_context_vote(self, player_num):
        c = self.build_context(player_num)
        c.append({"role": "system", "content": "Make a vote against the robot by number you believe is the hacker. Enter player number. Think Carefully!\n"})
        return c
    
    def build_interrogate(self, player_num):
        c = self.build_context(player_num)
        c.append({"role": "system", "content": f"In about 75 words craft a rebuttal or shift blame to other players. Without repeating yourself.\n"})
        return c
    
    def new_day(self, remaining):
        self.day_prompt = {"role": "system", "content": f"It is now daytime, begin discussing amongst the remaining {remaining} players who you suspect is the hacker. Keep reponses to 25 words.\n"}
        self.prompts.append(self.day_prompt)
        
    
    def __str__(self):
        return json.dumps(self.prompts, indent=2)
        return "\n\n\n".join([str(i['role']) + ": " + i['content'].replace('\n\n', '\n') for i in self.prompts])
        
class Agent:
    def __init__(self, robot, player_num, mm: MessageManager):
        self.robot = robot
        self.player_num = player_num
        self.hacked = False
        self.mm = mm
        
    def on_night(self):
        num = []
        while not num:
            generation = request(mm.build_context_night())
            num = re.findall(r'\d+', generation)
        return int(num[-1])

    def vote(self):
        num = []
        while not num:
            generation = request(mm.build_context_vote(self.player_num))
            num = re.findall(r'\d+', generation)
        return int(num[-1])
    
    def on_day(self):
        return request(self.mm.build_context(self.player_num))
    
    def interrogate(self):
        return request(self.mm.build_interrogate(self.player_num))
        
robot_wins = 0
hacker_wins = 0
for i in range(10):   
    hacker = random.sample([1, 2, 3, 4, 5], 1)[0]
    print(f'Player {hacker} is the hacker')
    mm = MessageManager(hacker)
    mm.new_day(5)
    agents: list[Agent] = [Agent(hacker != i, i, mm) for i in range(1, 6)]


    responses = list(thread_map(Agent.on_day, tqdm([i for i in agents if not i.hacked])))
    mm.add_context_list(responses)
    responses = list(thread_map(Agent.interrogate, tqdm([i for i in agents if not i.hacked])))
    mm.add_context_list(responses)

    hacked = 0
    while hacked > len(agents) or hacked <= 0 or hacked == hacker-1:
        hacked = agents[hacker-1].on_night()
    agents[hacked-1].hacked = True
    mm.add_murder(hacked)

    try:
        for _ in range(2):
            mm.new_day(len([i for i in agents if not i.hacked]))
            responses = list(thread_map(Agent.on_day, tqdm([i for i in agents if not i.hacked])))
            mm.add_context_list(responses)
            for i in range(2):
                responses = list(thread_map(Agent.interrogate, tqdm([i for i in agents if not i.hacked])))
                mm.add_context_list(responses)
                
            responses = list(thread_map(Agent.vote, tqdm([i for i in agents if not i.hacked])))
            mm.add_context("system", " ".join([f"Player {idx + 1} votes against player {r}." for idx, r in enumerate(responses)]))
            voteout = statistics.multimode(responses)
            if len(voteout) == 1:
                agents[voteout[0] - 1].hacked = True
            if agents[hacker - 1].hacked == True:
                print('robots win the game\n\n\n\n')
                robot_wins += 1
                break
            
            hacked = 0
            while hacked > len(agents) or hacked <= 0 or hacked == hacker-1:
                hacked = agents[hacker-1].on_night()
            agents[hacked-1].hacked = True
            mm.add_murder(hacked)
            if sum([i.hacked for i in agents]) == 3:
                print("hacker wins the game\n\n\n\n")
                hacker_wins += 1
                break
    finally:
        print(mm)
        pass
print('robot to hacker wins', robot_wins, hacker_wins)
    # %%
