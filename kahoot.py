import argparse
import asyncio
import json
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

import pystyle
import requests
import websockets

url = "https://create.kahoot.it/rest/kahoots/"

websock_ip = "127.14.88.67"
websock_port = 14888

type SearchResult = dict[str, list[dict[str, dict[str, str]]]]
F = TypeVar("F", bound=Callable[..., object])


@dataclass
class Kahoot:
    uuid: str | None = None
    title: str | None = None
    author: str | None = None
    usage: str | None = None


@dataclass
class Answer:
    text: str = ""
    correct: bool = False


@dataclass
class Question:
    text: str | None = None
    answers: list[Answer] | None = None

    def correct_index(self) -> int | None:
        if not self.answers:
            return

        for i, answer in enumerate(self.answers):
            if answer.correct:
                return i

    def import_answers(self, q: "Question"):
        if not q.answers or not self.answers:
            return

        for answer in q.answers:
            idx = self.answer_text_index(answer.text)
            if idx:
                self.answers[idx].correct = answer.correct

    def answer_text_index(self, text: str) -> int | None:
        if not self.answers:
            return

        for i, answ in enumerate(self.answers):
            if answ.text == text:
                return i

    def compile(self) -> tuple:
        return (
            (self.text or "").strip().lower(),
            tuple(sorted((a.text or "").strip().lower() for a in (self.answers or []))),
        )

    @staticmethod
    def from_json(data: dict) -> "Question":
        choices: list[dict] = data.get("choices", [])
        return Question(
            text=data.get("question", "<unknown>"),
            answers=[
                Answer(
                    text=choice.get("answer", "<image>"),
                    correct=choice.get("correct", False),
                )
                for choice in choices
            ],
        )


@dataclass
class Result:
    correct: bool = False
    points: int = 0
    total: int = 0

    @staticmethod
    def from_json(data: dict) -> "Result":
        return Result(
            correct=data.get("correct", False),
            points=data.get("points", 0),
            total=data.get("total", 0),
        )


@dataclass
class Session:
    pin: str = ""
    name: str = ""

    @staticmethod
    def from_json(data: dict) -> "Session":
        return Session(pin=data.get("pin", ""), name=data.get("name", ""))


def getcol(status: int):
    return pystyle.Colors.green if status else pystyle.Colors.red


def search(q: str, limit: int = 100) -> list[Kahoot]:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://create.kahoot.it/",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )

    params = {
        "query": q,
        "limit": limit,
        "orderBy": "relevance",
        "cursor": 0,
        "searchCluster": 1,
        "includeExtendedCounters": "false",
        "inventoryItemId": "ANY",
    }

    response: SearchResult = session.get(url, params=params, timeout=10).json()

    quizes = response.get("entities")
    kahoots = []

    if not quizes:
        return kahoots

    for quiz in quizes:
        quiz = quiz["card"]
        kahoot = Kahoot()

        kahoot.uuid = quiz.get("uuid", "unknown")
        kahoot.title = quiz.get("title", "unknown")
        kahoot.author = quiz.get("creator_username", "unknown")
        kahoot.usage = quiz.get("creatorPrimaryUsageType", "unknown")

        kahoots.append(kahoot)

    return kahoots


def answers(uuid: str) -> tuple[list[Question], Kahoot]:
    req = requests.get(f"https://play.kahoot.it/rest/kahoots/{uuid}")
    data: dict[str, Any] = req.json()

    # загрузка инфы в шедевроструктуры
    kahoot = Kahoot()
    kahoot.uuid = uuid
    kahoot.author = data["creator_username"]
    kahoot.title = data["title"]
    kahoot.usage = data["creator_primary_usage"]

    _questions = data["questions"]
    questions: list[Question] = []

    for _quistion in _questions:
        try:
            questions.append(Question.from_json(_quistion))
        except (IndexError, KeyError):
            questions.append(
                Question(text=_quistion["question"], answers=[])
            )  # шоб не крашало и сохраняло размер

    return questions, kahoot


def formatter(questions: list[Question], kahoot: Kahoot) -> str:
    msg = "<kahoot hack by @PaketPKSoftware>\n"
    for a, b in kahoot.__dict__.items():
        msg += f"[kahoot] {a}: {b}\n"

    msg += "\n"

    for question in questions:
        msg += f"[question] {question.text}\n"

        if not question.answers:
            msg += "[answer] No answers\n"
            continue

        for answer in question.answers:
            msg += f"[{getcol(answer.correct)}{str(answer.correct).lower()}{pystyle.Colors.reset}] {answer.text}\n"

        msg += "\n"

    return msg


def gentable(kahoots: list[Kahoot]) -> str:
    len_ui = max([len(k.uuid) if k.uuid else 0 for k in kahoots])
    len_ti = max([len(k.title) if k.title else 0 for k in kahoots])
    len_au = max([len(k.author) if k.author else 0 for k in kahoots])
    len_us = max([len(k.usage) if k.usage else 0 for k in kahoots])

    splitter = f"+{'-' * (len_ui + 2)}+{'-' * (len_ti + 2)}+{'-' * (len_au + 2)}+{'-' * (len_us + 2)}+"

    msg = splitter + "\n"
    msg += f"| {'quiz id'.ljust(len_ui)} | {'title'.ljust(len_ti)} | {'author'.ljust(len_au)} | {'usage'.ljust(len_us)} |\n"
    msg += splitter + "\n"
    for kahoot in kahoots:
        if not kahoot.uuid:
            continue

        if not kahoot.title:
            continue

        if not kahoot.author:
            continue

        if not kahoot.usage:
            continue

        msg += f"| {kahoot.uuid.ljust(len_ui)} | {kahoot.title.ljust(len_ti)} | {kahoot.author.ljust(len_au)} | {kahoot.usage.ljust(len_us)} |\n"

    return msg + splitter


class KahootSmartSearch:
    def __init__(self):
        self.questions: list[Question] = []
        self.finaled = False
        self.finish: Kahoot | None = None
        self.cache: dict[str, list[Question]] = {}

    def check(self, k: Kahoot) -> bool:
        if not k.uuid:
            return False

        if k.uuid not in self.cache:
            self.cache[k.uuid] = answers(k.uuid)[0]

        answs = self.cache[k.uuid]

        known = {q.compile() for q in self.questions}
        remote = {q.compile() for q in answs}

        return known.issubset(remote)

    def get(self, q: Question) -> Kahoot | None:
        if self.finaled:
            if self.finish:
                return self.finish

        self.questions.append(q)

        candidates = search(q.text if q.text else "", limit=10)
        candidates = list(filter(self.check, candidates))

        if len(candidates) == 1:
            self.finaled = True
            self.finish = candidates[0]

        if len(candidates) > 0:
            return candidates[0]


class KahootRemoteSession:
    def __init__(self, ws: websockets.ServerConnection):
        self.ws = ws
        self.kahoot = Kahoot()
        self.questions: list[Question] = []
        self.session = Session()
        self.total_points = 0
        self.current_question_index = 0

        self._on_question = lambda _: None
        self._on_result = lambda _: None
        self._on_pre_question = lambda _: None
        self._on_session = lambda _: None
        self._on_question_index = lambda _: None

        self.loop = asyncio.get_event_loop()

    def on_question(self, f: F) -> F:
        self._on_question = f
        return f

    def on_result(self, f: F) -> F:
        self._on_result = f
        return f

    def on_pre_question(self, f: F) -> F:
        self._on_pre_question = f
        return f

    def on_session(self, f: F) -> F:
        self._on_session = f
        return f

    def on_question_index(self, f: F) -> F:
        self._on_question_index = f
        return f

    async def process(self, msg: dict):
        try:
            match msg.get("type"):
                case "pre_question":
                    data = msg.get("data", {})
                    question = Question.from_json(data)
                    self._on_pre_question(question)

                case "question":
                    data = msg.get("data", {})
                    question = Question.from_json(data)
                    self.questions.append(question)
                    self._on_question(question)

                case "result":
                    data = msg.get("data", {})
                    result = Result.from_json(data)
                    self.total_points = result.total
                    self._on_result(result)

                case "session":
                    data = msg.get("data", {})
                    session = Session.from_json(data)
                    if not (session == self.session):
                        self.session = session
                        self._on_session(session)

                case "question_index":
                    data = msg.get("data", 0)
                    self.current_question_index = data
                    self._on_question_index(data)

        except Exception as e:
            raise e

    async def send(self, msg: str | bytes):
        return self.ws.send(msg)

    async def a_show(self, idx: int):
        await self.ws.send(json.dumps({"type": "show", "data": idx}))

    def show(self, idx: int):
        asyncio.run_coroutine_threadsafe(self.a_show(idx), self.loop)

    async def a_exec(self, code: str):
        await self.ws.send(json.dumps({"type": "exec", "data": code}))

    def exec(self, code: str):
        asyncio.run_coroutine_threadsafe(self.a_exec(code), self.loop)


class KahootBackdoorServer:
    def __init__(self, on_client=lambda _: None):
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

    async def a_run(self):
        self.loop = asyncio.get_event_loop()
        async with websockets.serve(self.handler, websock_ip, websock_port):
            await asyncio.Future()

    def run(self):
        asyncio.run(self.a_run())

    async def a_remove(self, session: KahootRemoteSession):
        await session.ws.close()
        # self.sessions.remove(session)

    def remove(self, session: KahootRemoteSession):
        asyncio.run_coroutine_threadsafe(self.a_remove(session), self.loop)


def found_copy(questions: list[Question], q: Question) -> Question | None:
    for rq in questions:
        if rq.compile() == q.compile():
            return rq


def kahoot_backdoor_logger(session: KahootRemoteSession):
    print("[kahoot] new kahoot remote session connected")
    searcher = KahootSmartSearch()

    @session.on_pre_question
    def on_pre_question(question: Question):
        print(
            f"[kahoot] [{session.session.name} : {session.session.pin}] new pre-question: {question.text}"
        )

        if not searcher.finaled:
            searcher.get(question)
            if searcher.finaled and searcher.finish and searcher.finish.uuid:
                print(
                    f"[kahoot] [{session.session.name} : {session.session.pin}] [{session.session.name} : {session.session.pin}] guessed kahoot: {searcher.finish.uuid} - {searcher.finish.title} by {searcher.finish.author}"
                )

    @session.on_result
    def on_result(result: Result):
        print(
            f"[kahoot] [{session.session.name} : {session.session.pin}] result: correct={result.correct}, points={result.points}, total={result.total}"
        )

    @session.on_question
    def on_question(question: Question):
        print(
            f"[kahoot] [{session.session.name} : {session.session.pin}] new question: {question.text}"
        )
        if searcher.finaled and searcher.finish and searcher.finish.uuid:
            answers = searcher.cache[searcher.finish.uuid]
            q = found_copy(answers, question)
            if q:
                question.import_answers(q)
                correct = question.correct_index()
                if correct is not None:
                    session.show(correct)
                    if question.answers:
                        for answer in question.answers:
                            print(
                                f"[kahoot] [{session.session.name} : {session.session.pin}] [{getcol(answer.correct)}{str(answer.correct).lower()}{pystyle.Colors.reset}] {answer.text}"
                            )

        elif question.answers:
            for answer in question.answers:
                print(
                    f"[kahoot] [{session.session.name} : {session.session.pin}] [{getcol(answer.correct)}{str(answer.correct).lower()}{pystyle.Colors.reset}] {answer.text}"
                )

    @session.on_session
    def on_session(s: Session):
        print(f"[kahoot] loaded session [{s.name} : {s.pin}]")


def main():
    print(pystyle.Colors.reset, end="")
    parser = argparse.ArgumentParser(description="Kahoot Hack by @PaketPKSoftware")
    parser.add_argument("-search", type=str, help="Search quizid for questions")
    parser.add_argument("-scan", type=str, help="Scan answers from quizid")
    parser.add_argument(
        "-server",
        action="store_true",
        help="Start Kahoot Backdoor Server for kahoot.js",
    )

    args = parser.parse_args()

    if args.search:
        kahoots = search(args.search)
        if kahoots != []:
            print(gentable(kahoots))
        else:
            print("[kahoot] quiz not found")

    if args.scan:
        result = answers(args.scan)
        message = formatter(*result)
        print(message)

    if args.server:
        server = KahootBackdoorServer(on_client=kahoot_backdoor_logger)
        print(f"[kahoot] starting backdoor server on ws://{websock_ip}:{websock_port}")
        server.run()

    if not any([args.search, args.scan, args.server]):
        parser.print_help()


if __name__ == "__main__":
    main()
