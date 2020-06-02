import json
import os.path
import numpy as np

from sys import exit

SECONDS_TO_NEW_CONVERSATION = 14400 # 4 hours

class Analyzer:
    message_data = None
    error = None
    message_file = None

    def __init__(self, message_file):
        self.message_file = message_file
        if not os.path.exists(message_file):
            self.error = f'{message_file} does not exist'
            return

        with open(message_file) as f:
            self.message_data = json.load(f)

        # Go through each message to count participants b/c particpants can leave
        

        if len(self.participants) != 2:
            self.error = f'There must be exactly 2 participants in the conversation.'
            return

        participants = set([self.participants[0]['name'], self.participants[1]['name']])

        for m in self.messages:
            if m['sender_name'] not in participants:
                self.error = f"{m['sender_name']} sent a message in a conversation between {participants}."
                return


    @property
    def messages(self):
        """
        Returns message of the conversation in ascending order by timestamp
        """
        messages = self.message_data['messages']
        return sorted(messages, key=lambda x: x['timestamp_ms'])

    @property
    def participants(self):
        return self.message_data['participants']

    @property
    def messages_split_by_participant(self):
        participant_a = self.participants[0]['name']
        participant_b = self.participants[1]['name']

        messages_a = [m for m in self.messages if m['sender_name'] == participant_a]
        messages_b = [m for m in self.messages if m['sender_name'] == participant_b]
        return messages_a, messages_b

    @property
    def conversations(self):
        conversations = []
        curr_conversation = []
        prev_message = None
        for m in self.messages:
            if not prev_message:
                prev_message = m
                curr_conversation.append(m)
                continue
            seconds_since_last_message = (m['timestamp_ms'] - prev_message['timestamp_ms']) / 1000
            if seconds_since_last_message >= SECONDS_TO_NEW_CONVERSATION:
                conversations.append(curr_conversation.copy())
                curr_conversation = []
            prev_message = m
            curr_conversation.append(m)
        return conversations

    def get_who_started_conversation_data(self):
        participant_a = self.participants[0]['name']
        participant_b = self.participants[1]['name']

        result = {}
        result[participant_a] = 0
        result[participant_b] = 0

        for c in self.conversations:
            result[c[0]['sender_name']] += 1
    
        return result

    def get_who_spoke_last_data(self):
        participant_a = self.participants[0]['name']
        participant_b = self.participants[1]['name']

        result = {}
        result[participant_a] = 0
        result[participant_b] = 0

        for c in self.conversations:
            result[c[-1]['sender_name']] += 1
    
        return result

    def get_75_percentile_length_text_data(self):
        """
        Gets the 75th percentile longest text length for each participant.
        """
        result = {}
        messages_a, messages_b = self.messages_split_by_participant

        def get_percentile(messages, percentile):
            if len(messages) == 0:
                return 0
            sorted_messages = sorted(messages, key=lambda x: len(x['content']) if 'content' in x else 0)
            message_lengths = list(map(lambda x: len(x['content']) if 'content' in x else 0, sorted_messages))
            numpy_arr = np.array(message_lengths)
            return np.percentile(numpy_arr, percentile)

        result[self.participants[0]['name']] = get_percentile(messages_a, 75)
        result[self.participants[1]['name']] = get_percentile(messages_b, 75)
        return result

    def get_questions_asked_data(self):
        messages_a, messages_b = self.messages_split_by_participant

        def is_question(message):
            if 'content' not in message:
                return False
            return '?' in message['content']
                
        a = sum( is_question(m) for m in messages_a )
        b = sum( is_question(m) for m in messages_b )

        result = {}
        result[self.participants[0]['name']] = a
        result[self.participants[1]['name']] = b
        return result

    def get_80_percentile_response_time_data(self):
        participant_a = self.participants[0]['name']
        participant_b = self.participants[1]['name']

        millisecond_differences_a = []
        millisecond_differences_b = []

        prev_message = None
        for m in self.messages:
            if not prev_message:
                prev_message = m
                continue
            if prev_message['sender_name'] != participant_b:
                prev_message = m
                continue
            if m['sender_name'] != participant_a:
                prev_message = m
                continue
            difference = m['timestamp_ms'] - prev_message['timestamp_ms']
            millisecond_differences_a.append(difference)
            prev_message = m

        prev_message = None
        for m in self.messages:
            if not prev_message:
                prev_message = m
                continue
            if prev_message['sender_name'] != participant_a:
                prev_message = m
                continue
            if m['sender_name'] != participant_b:
                prev_message = m
                continue
            difference = m['timestamp_ms'] - prev_message['timestamp_ms']
            millisecond_differences_b.append(difference)
            prev_message = m

        numpy_arr_a = np.array(millisecond_differences_a)
        numpy_arr_b = np.array(millisecond_differences_b)

        a_percentile = np.percentile(numpy_arr_a, 75) if len(millisecond_differences_a) > 0 else 0
        b_percentile = np.percentile(numpy_arr_b, 75) if len(millisecond_differences_b) > 0 else 0

        result = {}
        result[self.participants[0]['name']] = a_percentile
        result[self.participants[1]['name']] = b_percentile
        return result

    def get_scores(self):
        participant_a = self.participants[0]['name']
        participant_b = self.participants[1]['name']
        scores = {}
        scores[participant_a] = 0
        scores[participant_b] = 0

        data = self.get_who_started_conversation_data()
        result = apply_gradient(data)
        scores[participant_a] += result[participant_b]
        scores[participant_b] += result[participant_a]
        
        data = self.get_who_spoke_last_data()
        result = apply_gradient(data)
        scores[participant_a] += result[participant_b]
        scores[participant_b] += result[participant_a]

        data = self.get_75_percentile_length_text_data()
        result = apply_gradient(data)
        scores[participant_a] += result[participant_b]
        scores[participant_b] += result[participant_a]

        data = self.get_questions_asked_data()
        result = apply_gradient(data)
        scores[participant_a] += result[participant_b]
        scores[participant_b] += result[participant_a]

        data = self.get_80_percentile_response_time_data()
        result = apply_gradient(data)
        scores[participant_a] += result[participant_a]
        scores[participant_b] += result[participant_b]

        return scores

    def print_all_results(self):
        print(f'Who started convos more? {self.get_who_started_conversation_data()}')
        print(f'Who spoke last more? {self.get_who_spoke_last_data()}')
        print(f'75 percentile length text: {self.get_75_percentile_length_text_data()}')
        print(f'Questions asked: {self.get_questions_asked_data()}')
        print(f'80 percentile response times: {self.get_80_percentile_response_time_data()}')

    def get_amount_into_text(self):
        participant_a = self.participants[0]['name']
        participant_b = self.participants[1]['name']
        scores = self.get_scores()
        total = 0
        for k, v in scores.items():
            total += v
        if total == 0:
            return 0.5
        middle = total / 2
        crush_percentage = int(round(abs(middle - scores[participant_a]) / middle * 100))
        if crush_percentage == 0:
            return f'{participant_a} and {participant_b} are equally into each other'
        elif scores[participant_a] - middle > 0:
            return f'{participant_b} is {crush_percentage}% more into {participant_a}'
        else:
            return f'{participant_a} is {crush_percentage}% more into {participant_b}'


def apply_gradient(data):
    """
    Takes a scores like {'foo': 1, 'bar': 3} and converts it into
    {'foo': 0.25, 'bar': 0.75}
    """
    total = 0
    result = data.copy()
    for v in data.values():
        total += v
    for k in result:
        if total == 0:
            result[k] = 0
            continue
        result[k] /= total
    return result

def analyze(message_file):
    analyzer = Analyzer(message_file)
    if analyzer.error:
        print(analyzer.error)
        return
    print(analyzer.get_amount_into_text())
    analyzer.print_all_results()
