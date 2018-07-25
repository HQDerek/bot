""" Module for replaying a given game """
from glob import glob
from json import load, dump
import os
import webbrowser
from pandas import DataFrame
from question import Question
from bot import HqTriviaBot

class Replayer(object):
    """ One instance of the game Replayer """
    def __init__(self):
        self.questions = self.load_questions()

    @staticmethod
    def load_questions():
        """ Create a list of Question objects to replay """
        questions = []
        game_paths = [filename for filename in glob('games/*.json')]
        for game_path in game_paths:
            game_data = load(open(game_path))
            for question in game_data['questions']:
                questions.append(Question(is_replay=True, **question))
        questions.sort(key=lambda q:q.number)
        return questions

    def play(self):
        """ Play all questions loaded from saved games """
        bot = HqTriviaBot()
        self.setup_output_file()
        for question in self.questions:
            bot.prediction_time(question)

    @classmethod
    def setup_output_file(cls, mode='r+'):
        """ Create or load replayer output file. Is class method so it can be
        tested without instantiating class (calls load_questions) but still needs
        access to class to call itself recursively to handle exception """
        try:
            with open('replay_results.json', mode) as file:
                output = load(file) if mode == 'r+' else []
                output.append([])
                file.seek(0)
                dump(output, file, ensure_ascii=False, sort_keys=True, indent=4)
        except FileNotFoundError:
            cls.setup_output_file(mode='w+')

    @staticmethod
    def gen_report():
        """ Generate HTML report for replays """
        with open('replay_results.json', 'r') as file:
            replays = load(file)
            max_q_index = len(replays[0]) - 1
            trimmed_replays = [replay[:max_q_index] if len(replay) > (max_q_index + 1) \
                                else replay for replay in replays]

        col_names = []
        run_results = []
        for replay_index, replay in enumerate(trimmed_replays):
            run_result = []
            for q_idx, question_kwargs in enumerate(replay):
                question = Question(is_replay=True, **question_kwargs)

                if replay_index == 0:
                    run_result.append(1 if question.answered_correctly else -1)
                    col_names.append("#{} \n {}".format(question.number, question.id))
                else:
                    try:
                        if question.prediction['answer'] == trimmed_replays[0][q_idx]['prediction']['answer']:
                            run_result.append(0)
                        elif question.answered_correctly:
                            run_result.append(1)
                        else:
                            run_result.append(-1)
                    except IndexError:
                            run_result.append(0)

            run_results.append(run_result)

        data_frame = DataFrame(columns=col_names, data=run_results)
        with open('report_template.html', 'r') as file:
            template_string = file.read().replace('\n', '')
        html = template_string % data_frame.to_html(classes='replay-table').replace('border="1"', 'border="0"')
        path = os.path.abspath('replay_report.html')
        url = 'file://' + path

        with open(path, 'w') as file:
            file.write(html)
        webbrowser.open(url)
