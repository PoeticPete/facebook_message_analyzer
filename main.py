import fire
from analyzer import analyze


def hello(message_file='message_1.json'):
  return analyze(message_file)

if __name__ == '__main__':
  fire.Fire(hello)