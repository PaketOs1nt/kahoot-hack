"""
я не умею говорить на русском, так что документация будет написана на пайтоне
"""

import kahoot

kahoot.Kahoot # обьект датакласса (ну или структура) с 4 полями, uuid (quizid), title, author, usage (применение)

kahoot.Answer # обьект ответа на вопрос, поля: text (текст ответа), correct (верный ли ответ, True/False) 

kahoot.Question # обьект вопроса в викторине, поля: text (сам вопрос), answers (список обьяктов Answer), есть функция correct_index, возвращает индекс первого верного ответа


# допустим мы хотим получить список кахутов по какому то тексту
q = 'порна'
kahoots = kahoot.search(q) # теперь в kahoots есть список из обьектов kahoot.Kahoot
# так же есть аргумент limit, по дефолту стоит максимум, тоесть 100, больше 100 кахут будет выдавать ошибку
# его можно изменить напрямую указав kahoot.search(q, limit=10)

for k in kahoots:
    print(f"Найден QuizID по запросу '{q}': {k.uuid}") # мы можем сделать такое с разными полями обьекта Kahoot

# вывод будет:
"""
Найден QuizID по запросу 'порна': 9ac15e1f-a61b-4ee1-9398-ab66b42c7d47
Найден QuizID по запросу 'порна': a8f39c65-b144-4f78-b35f-9fc1d2a4274a
Найден QuizID по запросу 'порна': 6d08b0e9-48d0-4053-b564-54bed01feea8
Найден QuizID по запросу 'порна': b07c73af-4bdd-40d5-a9ab-e8f2aa9ac18f
"""

# ну допустим, мы уже знаем QuizID, как же тогда получить ответы? kahoot.answers!

questions, ka = kahoot.answers('b07c73af-4bdd-40d5-a9ab-e8f2aa9ac18f') # kahoot.answers возвращает два обьекта, (список из kahoot.Question, и kahoot.Kahoot)

print(f"ответы на викторину {ka.title}:\n")

for question in questions:
    print(f"вопрос: {question.text}")
    print(f"найден правильный ответ: {question.answers[question.correct_index()].text}")

    print()

# вывод к этому примеру:
"""
ответы на викторину Штребунал:

вопрос: Кто это?
найден правильный ответ: Штребух

вопрос: Правда ли,что такие мемы называют "пост иронией"?
найден правильный ответ: True

вопрос: Кто тут изображён?
найден правильный ответ: Ученики КГУ "Школа номер 10 г. Житикары"

вопрос: Правда ли,что пароль "Хуйпидора228СС_ГОЙДАГООЛ144881416" Можно установить вна сайте Гей порна?
найден правильный ответ: False

вопрос: Сколько гражданских лиц Украины погибло на момент 22 июн. 24 года
найден правильный ответ: Недостаточно
"""

# теперь вы знаете как можно очень просто сделать свой чит на kahoot

# новая тема - удаленный доступ к кахут сессии браузера!
# эт конешна оч сложно но думаю похуй потому что я постарался сделать это просто

kahoot.Result # простая структура, имеет только поля correct (верный наш ответ был или нет) и points (сколько балов мы получили), так же total (сколько у нас баллов всего)

kahoot.Session # простая структура, поля: pin (str), name (str) , тоесть пин кахута и имя игрока

kahoot.KahootBackdoorServer # обьект сервера, через него мы будем все делать и тд

kahoot.KahootRemoteSession # обьект доступа к клиенту, тоесть доступ к подключенной сессии который мы через kahoot.KahootBackdoorServer получили

kahoot.KahootSmartSearch # умный поисковик кахутов по вопросам, но для этого нам надо не текст вопроса а сам вопрос, что бы он мог сравнивать ответы и так далее


# создание сервера: надо создатьь функцию обработчик клиентов, и запустить сервер с ним

def handler(connected: kahoot.KahootRemoteSession):
    # теперь нам надо сделать обработчики для самого клиента, например что бы мы выводили все результаты ответов
    @connected.on_result # что бы connected знал какую функцию вызывать когда приишел результат
    def on_result(result: kahoot.Result):
        print(f"ответ верный: {result.correct}\nбаллы за вопрос: {result.points}\nвсего у нас баллов: {result.total}\n")

    # и что бы выводило какие ответы у нас грузятся: (по умолчанию все не правильные)
    @connected.on_pre_question # что бы connected знал какую функцию вызывать когда грузиться вопрос
    def on_pre_question(question: kahoot.Question):
        print(f"грузиться вопрос: {question.text}\n")

    @connected.on_session
    def on_session(session: kahoot.Session):
        print(f"подключен к сессии: {session.name} : {session.pin}\n")

    # так же мы можем с connected.on_question, connected.on_question_index (пишет какой текущий вопрос, начинаеться с нуля конечно же)

    # так же мы можем подсветить кнопку ответа через connected.show(index), индекс начинаеться с нуля
    # !!!!!!!!!!!!!!! connected.show(index) просто делает тень выбранного ответа чуть чуть прозрачнее
    # !!!!!!!!!!!!!!! что бы найти то что подсветилось надо прям всматриваться

    # так же есть connected.exec(str) что бы выполнить js код прям в браузере подключенного

    # у самого connected есть поля
    connected.total_points: int                                                                                                          # type: ignore
    connected.session: kahoot.Session                                                                                                    # type: ignore
    connected.current_question_index: int                                                                                                # type: ignore
    connected.questions: list[kahoot.Question] # уже загруженные вопросы                                                                 # type: ignore

server = kahoot.KahootBackdoorServer(handler)

# !!!!!!!!!!!
# !!!!!!!!!!!
# !!!!!!!!!!!
# !!!!!11!!11 главное - что бы подключиться к серверу надо обязательно заинжектить kahoot.js в вкладку кахута через DevTools !!!!!!!!!!!!
# !!!!!!!!!!!
# !!!!!!!!!!!
# !!!!!!!!!!!

# у server по дефолту лимит активных подключений - 1, если нам надо это исправить, надо прямо заявить:
server.limit = 5
server.sessions: list[kahoot.KahootRemoteSession] # список всех подключенных kahoot.KahootRemoteSession                                 # type: ignore

# запуск сервера: server.run(), но оно блочит поток, так что советую запусать в отдельном потоке

# и теперь как юзать searcher
searcher = kahoot.KahootSmartSearch()

result = searcher.get(questions[0]) # используем первый вопрос из того кахута в начале
result = searcher.get(questions[1]) # и грузим второй что бы он имел больше данных для анализа

print(searcher.finaled) # finaled означает закончили мы поиск полностью и имеем один стойкий результат или нет
print(searcher.finish) # finish - финальный точный кахут, он есть только если finaled == True

"""
вывод:
True
Kahoot(uuid='b07c73af-4bdd-40d5-a9ab-e8f2aa9ac18f', title='Штребунал', author='ZmeiOdnoglazi', usage='unknown')

это означает что наш поисковик смог найтии этот кахут по 2 первым вопросам,
это особенно подходит если мы делаем сервер поисковик, хотя он уже есть: 
kahoot.kahoot_backdoor_logger - он уже имеет встроенный логгер и поисковик,
а так же подсвечивает верные ответы если нашел кахут
"""
