// ==UserScript==
// @name         Kahoot Backdoor
// @namespace    http://kahoot.it/
// @version      1.0
// @description  Kahoot Backdoor
// @match        *://kahoot.it/*
// @grant        none
// @run-at       document-start
// ==/UserScript==
(function() {
const OriginalWebSocket = window.WebSocket;

const backdoor = new OriginalWebSocket('ws://127.14.88.67:14888');

function FindByAttributeValue(attribute, value, element_type)   {
    element_type = element_type || "*";
    var All = document.getElementsByTagName(element_type);
    for (var i = 0; i < All.length; i++)       {
        if (All[i].getAttribute(attribute) == value) { return All[i]; }
    }
}

function compileQuestion(q) {
    return JSON.stringify({
        data: q,
        type: "question"
    });
}

function compilePreQuestion(q) {
    return JSON.stringify({
        data: q,
        type: "pre_question"
    });
}

function compileResult(q) {
    return JSON.stringify({
        data: q,
        type: "result"
    });
}

function compileSession(q) {
    return JSON.stringify({
        data: q,
        type: "session"
    });
}

function compileQuestionIndex(q) {
    return JSON.stringify({
        data: q,
        type: "question_index"
    });
}

function show(index) {
    FindByAttributeValue("data-functional-selector", 'answer-'+index, "button").style.boxShadow = 'rgba(0, 0, 0, 0.15) 0px -4.735px 0px 0px inset';
}

window.WebSocket = function (...args) {
    const ws = new OriginalWebSocket(...args);

    const origSend = ws.send;
    ws.send = function (data) {
        return origSend.call(this, data);
    };

    ws.addEventListener("message", (event) => {
        try {
            const msg = JSON.parse(event.data)[0];
            if (!msg?.data?.content) return;

            const data = JSON.parse(msg.data.content);

            if (data?.playerName && msg?.data?.gameid) {
                backdoor.send(compileSession({
                    name: data.playerName,
                    pin: msg.data.gameid
                }))
            }

            try {
                const question = {
                    question: data.title,
                    choices: data.choices.map(c => ({
                        answer: c.answer ?? "<image>",
                        correct: false
                    }))
                };
                if (Object.keys(question).length === 0) return;

                if (
                    "getReadyTimeRemaining" in data
                ) {
                    backdoor.send(compilePreQuestion(question));
                    backdoor.send(compileQuestionIndex(data.questionIndex));

                } else {
                    backdoor.send(compileQuestion(question));
                }
            } catch (e) {
                if ("isCorrect" in data || "points" in data) {
                    const result = {
                        correct: data.isCorrect,
                        points: data.points,
                        total: data.totalScore
                    };
                    backdoor.send(compileResult(result));
                }
            }

        } catch (e) {
        }
    });

    return ws;
};

backdoor.onmessage = function(event) {
    try {
        const msg = JSON.parse(event.data);
        if (msg.type === "show") {
            setTimeout(() => {
                show(msg.data);
            }, 200);
        }

        if (msg.type === "exec") {
            setTimeout(() => {
                try {new Function(msg.data)();} catch {}
            }, 0);
        }
    } catch (e) {
    }
}
})();

