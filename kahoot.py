from dataclasses import dataclass

import requests
import argparse, json
import pystyle

url = "https://create.kahoot.it/rest/kahoots/"

@dataclass
class Kahoot:
    uuid: str | None = None
    title: str | None = None
    author: str | None = None
    usage: str | None = None

@dataclass
class Answer:
    text: str | None = None
    correct: bool | None = None

@dataclass
class Question:
    text: str | None = None
    answers: list[Answer] | None = None

def search(q: str) -> list[Kahoot]:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://create.kahoot.it/",
        "Accept-Language": "en-US,en;q=0.9"
    })

    params = {
        'query': q,
        'limit': 100,
        'orderBy': 'relevance',
        'cursor': 0,
        'searchCluster': 1,
        'includeExtendedCounters': 'false',
        'inventoryItemId': 'ANY'
    }

    response = session.get(url, params=params, timeout=10).json()

    quizes = response.get('entities')
    kahoots = []
    for quiz in quizes:
        quiz = quiz['card']
        kahoot = Kahoot()

        kahoot.uuid = quiz.get('uuid', 'unknown')
        kahoot.title = quiz.get('title', 'unknown')
        kahoot.author = quiz.get('creator_username', 'unknown')
        kahoot.usage = quiz.get('creatorPrimaryUsageType', 'unknown')

        kahoots.append(kahoot)
    
    return kahoots

def answers(uuid: str) -> tuple[list[Question], Kahoot]:
    req = requests.get(f'https://play.kahoot.it/rest/kahoots/{uuid}')
    data = req.json() 

    # загрузка инфы в шедевроструктуры
    kahoot = Kahoot()
    kahoot.uuid = uuid
    kahoot.author = data["creator_username"]
    kahoot.title = data["title"]
    kahoot.usage = data["creator_primary_usage"]

    _questions = data['questions']
    questions: list[Question] = []

    for _quistion in _questions:
        choices = _quistion['choices']
        questions.append(Question(
            text=_quistion['question'],
            answers=[
                Answer(
                    text=choice['answer'],
                    correct=choice['correct']
                ) for choice in choices
            ]
        ))

    return questions, kahoot

def formatter(questions: list[Question], kahoot: Kahoot) -> str:
    msg = "<kahoot hack by @PaketPKSoftware>\n"
    for a, b in kahoot.__dict__.items():
        msg += f'[kahoot] {a}: {b}\n'

    msg += '\n'

    getcol = lambda status: pystyle.Colors.green if status else pystyle.Colors.red

    for question in questions:
        msg += f'[question] {question.text}\n'
        for answer in question.answers:
            msg += f"[{getcol(answer.correct)}{str(answer.correct).lower()}{pystyle.Colors.reset}] {answer.text}\n"
        
        msg += '\n'

    return msg

def gentable(kahoots: list[Kahoot]):
    len_ui = max(*[len(k.uuid) for k in kahoots])
    len_ti = max(*[len(k.title) for k in kahoots])
    len_au = max(*[len(k.author) for k in kahoots])
    len_us = max(*[len(k.usage) for k in kahoots])

    splitter = f"+{'-'*(len_ui+2)}+{'-'*(len_ti+2)}+{'-'*(len_au+2)}+{'-'*(len_us+2)}+"

    msg = splitter + '\n'
    msg += f"| {'quiz id'.ljust(len_ui)} | {'title'.ljust(len_ti)} | {'author'.ljust(len_au)} | {'usage'.ljust(len_us)} |\n"
    msg += splitter + '\n'
    for kahoot in kahoots:
        msg += f"| {kahoot.uuid.ljust(len_ui)} | {kahoot.title.ljust(len_ti)} | {kahoot.author.ljust(len_au)} | {kahoot.usage.ljust(len_us)} |\n"
    
    return msg + splitter

def main():
    parser = argparse.ArgumentParser(description="Kahoot Hack by @PaketPKSoftware")
    parser.add_argument('-search', type=str, help="Search quizid for questions")
    parser.add_argument('-scan', type=str, help="Scan answers from quizid")

    args = parser.parse_args()

    if args.search:
        kahoots = search(args.search)
        if kahoots != []:
            print(
                gentable(kahoots)
            )
        else:
            print('[kahoot] quiz not found')

    if args.scan:
        answer = answers(args.scan)
        message = formatter(answer)
        print(message)

    if not any([args.search, args.scan]):
        parser.print_help()

if __name__ == '__main__':
    main()