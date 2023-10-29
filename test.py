# %%
import os
import openai
import random
from dotenv import load_dotenv

NUM_PLAYER = 5

def context(player):
    return f'''You are playing mafia, a party game with one hacker and 4 robots for a total of 5 robots.
Every night the hacker will choose a robot to kill. A hacked robot is no longer able to participate in the discussion.
In the morning the robots including the hacker converse in an attempt to reveal who the hacker is. This is followed with a vote on who to remove from the village.
The hacker loses if they are voted out of the game and wins if there is only one robot left.
Every player will be 'Player [a number from 1 to {NUM_PLAYER}]'

Once you have been eliminated, you're not supposed to take part in discussion and return the string "Hacked" and nothing else when it is your turn.

You are not simulating the game, so you shouldn't simulate what the response of others should be, 
instead just focus on your own response to the context. 

You are { 'the hacker' if player.is_hacker  else 'a robot'}.
You are player number {player.player_num}.
'''

class Agent:
    def __init__(self, is_hacker, player_num):
        self.is_hacker = is_hacker
        self.player_num = player_num
        self.context = []
        
    def on_night(self):
        if not self.is_hacker:
            return
        
        prompt = """It is now night time. Choose a robot to hack. Once you made your choice please 
        only return a response in this format "Player {your choice} has been eliminated" and nothing else"""
        return self.request(prompt)
    
    def on_day(self, day_response):
        prompt = '''It is now daytime, begin discussing amongst the other players who you suspect is the hacker. 
        You don't have access to any body language but just the context and responses from other players. 
        Keep reponses to less than 50 words.'''
        if None not in day_response:
            prompt += 'Here are the previous responses of other players, including youself:\n' + repr(day_response)
        return self.request(prompt)
    
    def request(self, prompt=None):
        messages = [{'role': 'system', 'content': context(self)}]
        if state_context:
            messages += [{'role': 'system', 'content': state_context}]
        messages += self.context
        messages += [{'role': 'user', 'content': prompt}]

        if state_context:
            messages.insert(1, {'role': 'system', 'content': state_context})

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages)

        if not response:
            raise ValueError('Failed to get API response')
        content = response.choices[0]['message']['content'].replace('\n', ' ').replace('\t', ' ')

        self.context.append({'role': 'assistant', 'content': content})
        return content
        
if __name__ == '__main__':
    load_dotenv()
    openai.api_key = os.getenv("OPENAI_KEY")

    hacker = random.randint(0, NUM_PLAYER)
    print(f'Player {hacker + 1} is the hacker!')
    players = [Agent(hacker == i, i) for i in range(1, NUM_PLAYER + 1)]

    night_num = 1
    state_context = ''

    while True:
        for player in players:
            if (x := player.on_night()):
                event = x
        
        state_context += f'\nNight {night_num}. {event}'
        print(state_context)

        statements = [None, None, None, None, None]
        while True:
            prev_statements = list(statements)
            for i, player in enumerate(players):
                response = player.on_day(prev_statements)
                statements[i] = {f'Player {player.player_num}': response}
                print(f'Player {player.player_num}:\n{response}')
                input("\nPress Enter to continue...\n")

        night_num += 1
        input("\nPress Enter to continue...\n")