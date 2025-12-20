from dataclasses import dataclass

import websockets
import requests
import argparse
import asyncio
import pystyle
import json

url = "https://create.kahoot.it/rest/kahoots/"

websock_ip = "127.14.88.67"
websock_port = 14888

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

    def correct_index(self) -> int | None:
        if self.answers is None:
            return None

        for i, answer in enumerate(self.answers):
            if answer.correct:
                return i
        
        return None

    def compile(self) -> tuple:
        return (
            (self.text or "").strip().lower(),
            tuple(sorted(
                (a.text or "").strip().lower()
                for a in (self.answers or [])
            ))
        )

    @staticmethod
    def from_json(data: dict) -> 'Question':
        choices: list[dict] = data.get('choices', [])
        return Question(
            text=data.get('question', "<unknown>"),
            answers=[
                Answer(
                    text=choice.get('answer', "<image>"),
                    correct=choice.get('correct', False)
                ) for choice in choices
            ]
        )

@dataclass
class Result:
    correct: bool = False
    points: int = 0

    @staticmethod
    def from_json(data: dict) -> 'Result':
        return Result(
            correct=data.get('correct', False),
            points=data.get('points', 0)
        )
        
def getcol(status: int):
    return pystyle.Colors.green if status else pystyle.Colors.red

def search(q: str, limit: int = 100) -> list[Kahoot]:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://create.kahoot.it/",
        "Accept-Language": "en-US,en;q=0.9"
    })

    params = {
        'query': q,
        'limit': limit,
        'orderBy': 'relevance',
        'cursor': 0,
        'searchCluster': 1,
        'includeExtendedCounters': 'false',
        'inventoryItemId': 'ANY'
    }

    response: dict = session.get(url, params=params, timeout=10).json()

    quizes = response.get('entities')
    kahoots = []
    for quiz in quizes:
        quiz: dict[str, str] = quiz['card']
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
        try:
            questions.append(Question.from_json(_quistion))
        except (IndexError, KeyError):
            questions.append(Question(text=_quistion['question'],answers=[])) # шоб не крашало и сохраняло размер

    return questions, kahoot

def formatter(questions: list[Question], kahoot: Kahoot) -> str:
    msg = "<kahoot hack by @PaketPKSoftware>\n"
    for a, b in kahoot.__dict__.items():
        msg += f'[kahoot] {a}: {b}\n'

    msg += '\n'

    for question in questions:
        msg += f'[question] {question.text}\n'
        for answer in question.answers:
            msg += f"[{getcol(answer.correct)}{str(answer.correct).lower()}{pystyle.Colors.reset}] {answer.text}\n"
        
        msg += '\n'

    return msg

def gentable(kahoots: list[Kahoot]) -> str:
    len_ui = max([len(k.uuid) for k in kahoots])
    len_ti = max([len(k.title) for k in kahoots])
    len_au = max([len(k.author) for k in kahoots])
    len_us = max([len(k.usage) for k in kahoots])

    splitter = f"+{'-'*(len_ui+2)}+{'-'*(len_ti+2)}+{'-'*(len_au+2)}+{'-'*(len_us+2)}+"

    msg = splitter + '\n'
    msg += f"| {'quiz id'.ljust(len_ui)} | {'title'.ljust(len_ti)} | {'author'.ljust(len_au)} | {'usage'.ljust(len_us)} |\n"
    msg += splitter + '\n'
    for kahoot in kahoots:
        msg += f"| {kahoot.uuid.ljust(len_ui)} | {kahoot.title.ljust(len_ti)} | {kahoot.author.ljust(len_au)} | {kahoot.usage.ljust(len_us)} |\n"
    
    return msg + splitter

class KahootSmartSearch:
    def __init__(self):
        self.questions: list[Question] = []
        self.finaled = False
        self.finish: Kahoot = None
        self.cache = {}
    
    def check(self, k: Kahoot) -> bool:
        if k.uuid not in self.cache:
            self.cache[k.uuid] = answers(k.uuid)[0]

        answs = self.cache[k.uuid]

        known = {q.compile() for q in self.questions}
        remote = {q.compile() for q in answs}

        return known.issubset(remote)
    
    def get(self, q: Question) -> Kahoot:
        if (self.finaled):
            return self.finish

        self.questions.append(q)

        candidates = search(q.text, limit=10)
        candidates = list(filter(self.check, candidates))

        if (len(candidates) == 1):
            self.finaled = True
            self.finish = candidates[0]

        if len(candidates) > 0:
            return candidates[0]

class KahootRemoteSession:
    def __init__(self, ws: websockets.ServerConnection):
        self.ws = ws
        self.kahoot = Kahoot()
        self.questions: list[Question] = []
        self.pin = ''

        self.on_question = lambda _: None
        self.on_result = lambda _: None
        self.on_pre_question = lambda _: None

    async def process(self, msg: dict):
        try:
            match msg.get('type'):
                case 'pre_question':
                    data = msg.get('data', {})
                    question = Question.from_json(data)
                    self.on_pre_question(question)

                case 'question':
                    data = msg.get('data', {})
                    question = Question.from_json(data)
                    self.questions.append(question)
                    self.on_question(question)

                case 'result':
                    data = msg.get('data', {})
                    result = Result.from_json(data)
                    self.on_result(result)

        except Exception:
            pass
                
    def send(self, msg: str | bytes):
        return self.ws.send(msg)
    
    async def show(self, idx: int):
        await self.ws.send(json.dumps({
            'type': 'show',
            'data': idx
        }))

class KahootBackdoorServer:
    def __init__(self, on_client = lambda _: None):
        self.sessions: list[KahootRemoteSession] = []
        self.limit = 1
        self.on_client = on_client

    def get(self) -> KahootRemoteSession | None:
        return self.sessions[0] if self.sessions else None

    async def handler(self, ws: websockets.ServerConnection):
        session = KahootRemoteSession(ws)
        if len(self.sessions) >= self.limit:
            await ws.close()
            return
        
        self.sessions.append(session)
        try:
            self.on_client(session)
            async for msg in ws:
                await session.process(json.loads(msg))
        finally:
            self.sessions.remove(session)

    async def run(self):
        async with websockets.serve(self.handler, websock_ip, websock_port):
            await asyncio.Future()

def kahoot_backdoor_logger(session: KahootRemoteSession):
    print('[kahoot] new kahoot remote session connected')
    searcher = KahootSmartSearch()

    def on_pre_question(question: Question):
        print(f'[kahoot] new pre-question: {question.text}')
        # for answer in question.answers:
        #     print(f"[{getcol(answer.correct)}{str(answer.correct).lower()}{pystyle.Colors.reset}] {answer.text}")

        if not searcher.finaled:
            searcher.get(question)
            if searcher.finaled:
                print(f'[kahoot] guessed kahoot: {searcher.finish.uuid} - {searcher.finish.title} by {searcher.finish.author}')

    def on_result(result: Result):
        print(f'[kahoot] result: correct={result.correct}, points={result.points}')

    def on_question(question: Question):
        print(f'[kahoot] new question: {question.text}')
        for answer in question.answers:
            print(f"[{getcol(answer.correct)}{str(answer.correct).lower()}{pystyle.Colors.reset}] {answer.text}")

        if searcher.finaled:
            answers = searcher.cache[searcher.finish.uuid]
            for answer in answers:
                if answer.text == question.text:
                    asyncio.create_task(session.show(answer.correct_index()))
                    break

    session.on_pre_question = on_pre_question
    session.on_question = on_question
    session.on_result = on_result

def main():
    parser = argparse.ArgumentParser(description="Kahoot Hack by @PaketPKSoftware")
    parser.add_argument('-search', type=str, help="Search quizid for questions")
    parser.add_argument('-scan', type=str, help="Scan answers from quizid")
    parser.add_argument('-server', action='store_true', help="Start Kahoot Backdoor Server for kahoot.js")

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
        result = answers(args.scan)
        message = formatter(*result)
        print(message)

    if args.server:
        server = KahootBackdoorServer(on_client=kahoot_backdoor_logger)
        print(f'[kahoot] starting backdoor server on ws://{websock_ip}:{websock_port}')
        asyncio.run(server.run())

    if not any([args.search, args.scan, args.server]):
        parser.print_help()

if __name__ == '__main__':
    main()
