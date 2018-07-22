from random import choice
from json import dumps
from question import Question

def generate_game(show_id=12345, num_correct=6, as_JSON=False):
    """ Generate a completed games saved json """

    choices = ['A', 'B', 'C']
    correct = choice(choices)

    game_data = {
        "numCorrect": num_correct,
        "prize": "$6500",
        "questonCount": 12,
        "ts": "2018-02-25T20:56:38.861Z",
        "showId": show_id,
        "questions": [{
            "questionId": show_id + i,
            "questionNumber": i + 1,
            "question": "This is a question, isn't it?",
            "answers": {
                "A": "First Answer",
                "B": "Second Answer",
                "C": "Third Answer"
            },
            "category": choice(['Educational', 'Sport', 'TV & Film', 'Politics', 'Geography']) ,
            "correct": correct,
            "prediction": {
                "answer": correct if i < num_correct else choices[choices.index(correct) - 1],
                "confidence": {
                    "A": "75%" if correct == "A" else "25%",
                    "B": "75%" if correct == "B" else "25%",
                    "C": "75%" if correct == "C" else "25%"
                }
            }
        } for i in range(12)]
    }

    return game_data if as_JSON is False else dumps(game_data)

def generate_question(is_replay=False, correct=False):
    """ Return a single instance of a Question """
    q_kwargs = {
        "questionId": 123,
        "questionNumber": 1,
        "question": "This is a question, isn't it?",
        "answers": {
            "A": "First Answer",
            "B": "Second Answer",
            "C": "Third Answer"
        },
        "category": 'Geography',
        "correct": 'B',
        "prediction": {
            "answer": 'B' if correct else 'C',
            "confidence": {
                "A": "0%",
                "B": "75%" if correct else "25%",
                "C": "75%" if not correct == "C" else "25%"
            }
        }
    }
    return Question(is_replay=is_replay, **q_kwargs)
