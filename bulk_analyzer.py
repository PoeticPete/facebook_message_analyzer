"""
Analyzes an entire directory from Facebook
"""
from analyzer import Analyzer
from sys import exit
import os


class BulkAnalyzer:
    message_file_paths = []
    _name = None

    def __init__(self, directory_path):
        if not directory_path:
            print("Must supply directory path")
            exit()
        if not os.path.exists(f'{directory_path}/inbox/'):
            print(f'{directory_path} does not exist')
            exit()
            return
        for directory in os.walk(f'{directory_path}/inbox/'):
            if 'message_1.json' in directory[2]:
                message_file = f'{directory[0]}/message_1.json'
                self.message_file_paths.append(message_file)


    @property
    def current_user_name(self):
        if self._name:
            return self._name
        names = {}
        for message_file in self.message_file_paths:
            analyzer = Analyzer(message_file)
            if analyzer.error:
                continue
            scores = analyzer.get_scores()
            for k in scores.keys():
                if k in names:
                    names[k] += 1
                else:
                    names[k] = 1
        for k in names:
            if names[k] > 2:
                self._name = k
                return k

    def get_analysis(self, minimum_messages=20):
        results = []
        analyzers = []
        for message_file in self.message_file_paths:
            analyzer = Analyzer(message_file)
            if analyzer.error:
                continue
            if len(analyzer.messages) >= minimum_messages:
                analyzers.append(analyzer)

        def get_amount_into(analyzer, name):
            total = 0
            for k, v in analyzer.get_scores().items():
                total += v
            if total == 0:
                return 0.5
            return analyzer.get_scores()[name] / total
            
        analyzers.sort(key=lambda analyzer: get_amount_into(analyzer, self.current_user_name), reverse=True)
        for analyzer in analyzers:
            results.append(analyzer.get_amount_into_text())
            # scores = analyzer.get_scores()
            # amount_into_percentage = get_amount_into(analyzer, self.current_user_name) * 100
            # for k in scores:
            #     if k != self.current_user_name:
            #         results.append(f'{k} is {amount_into_percentage}% into you')
            #         print(f'{k} is {amount_into_percentage}% into you')


        results.append('\nYour most common conversations are: ')
        analyzers.sort(key=lambda analyzer: len(analyzer.conversations), reverse=True)
        for analyzer in analyzers[:10]:
            results.append(analyzer.get_amount_into_text())
                    
        return results

def analyze_bulk(directory_path, minimum_messages=20):
    bulk_analyzer = BulkAnalyzer(directory_path)
    for result in bulk_analyzer.get_analysis():
        print(result)
