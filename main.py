import fire
from analyzer import analyze
from bulk_analyzer import analyze_bulk

class MessageAnalyzer(object):
  """A simple calculator class."""

  def analyze_file(self, message_file='message_1.json'):
    return analyze(message_file)

  def analyze_directory(self, message_directory):
    return analyze_bulk(message_directory)

if __name__ == '__main__':
  fire.Fire(MessageAnalyzer)