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

function show(index) {
    FindByAttributeValue("data-functional-selector", 'answer-'+index, "button").style.boxShadow = 'rgba(0, 0, 0, 0.15) 0px -4.735px 0px 0px inset';
}

window.WebSocket = function (...args) {
    const ws = new OriginalWebSocket(...args);

    const origSend = ws.send;
    ws.send = function (data) {
        //console.log("[WS OUT]", data);
        return origSend.call(this, data);
    };

    ws.addEventListener("message", (event) => {
        try {
            const msg = JSON.parse(event.data)[0];
            if (!msg?.data?.content) return;
            
            const data = JSON.parse(msg.data.content);

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
                    //console.log("[WS IN] pre-question detected");
                    backdoor.send(compilePreQuestion(question));

                } else {
                    //console.log("[WS IN] question detected");
                    backdoor.send(compileQuestion(question));
                }
            } catch (e) {
                if ("isCorrect" in data || "points" in data) {
                    const result = {
                        correct: data.isCorrect,
                        points: data.points
                    };
                    backdoor.send(compileResult(result));
                }
            }
        
        } catch (e) {
            //console.error("[WS IN] parse error:", e);
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
            }, 150);
        }
    } catch (e) {
    }
}