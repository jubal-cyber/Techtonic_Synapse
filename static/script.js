let teamId = null;
let teamName = null;
let teamCode = null;

let currentQuestion = 0;
let currentQuestionData = null;

let quizHasStarted = false;
let hasAnswered = false;

let stateInterval = null;


async function registerTeam() {

    const nameInput =
        document.getElementById("team-name");

    const codeInput =
        document.getElementById("team-code");

    const message =
        document.getElementById("register-message");

    teamName = nameInput.value.trim();
    teamCode = codeInput.value.trim().toUpperCase();

    message.textContent = "";

    if (!teamName) {
        message.textContent = "Please enter your team name.";
        return;
    }

    if (!teamCode) {
        message.textContent = "Please enter your team code.";
        return;
    }

    try {

        const response = await fetch("/register", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                team_name: teamName,
                team_code: teamCode
            })
        });

        const data = await response.json();

        if (!data.success) {

            message.textContent = data.message;
            return;
        }

        teamId = data.team_id;
        teamName = data.team_name;

        document.getElementById(
            "waiting-team"
        ).textContent = teamName;

        document.getElementById(
            "team-display"
        ).textContent = teamName;

        quizHasStarted = false;
        currentQuestion = 0;
        hasAnswered = false;

        showScreen("waiting-screen");

        startStatePolling();

    } catch (error) {

        console.error(error);

        message.textContent =
            "Could not connect to quiz server.";
    }
}


function startStatePolling() {

    if (stateInterval) {
        clearInterval(stateInterval);
    }

    checkState();

    stateInterval = setInterval(
        checkState,
        500
    );
}


async function checkState() {

    if (!teamId) {
        return;
    }

    try {

        const response =
            await fetch("/state");

        const data =
            await response.json();


        if (!data.started) {

            if (quizHasStarted) {

                quizHasStarted = false;

                showScreen("finished-screen");
            }

            return;
        }


        if (!quizHasStarted) {

            quizHasStarted = true;

            currentQuestion =
                data.current_question;

            hasAnswered = false;

            await loadQuestion(
                currentQuestion
            );

            updateTeamTimer(
                data.remaining
            );

            return;
        }


        if (
            data.current_question !==
            currentQuestion
        ) {

            currentQuestion =
                data.current_question;

            hasAnswered = false;

            await loadQuestion(
                currentQuestion
            );
        }


        if (!hasAnswered) {

            updateTeamTimer(
                data.remaining
            );
        }

    } catch (error) {

        console.log(
            "Connection error:",
            error
        );
    }
}


async function loadQuestion(questionId) {

    const response =
        await fetch(
            `/question/${questionId}`
        );

    const data =
        await response.json();

    if (!data.success) {
        return;
    }

    currentQuestionData =
        data.question;

    hasAnswered = false;

    document.getElementById(
        "question-id"
    ).textContent =
        data.question.id;

    document.getElementById(
        "question-text"
    ).textContent =
        data.question.question;

    document.getElementById(
        "answer-message"
    ).textContent = "";

    const optionsContainer =
        document.getElementById(
            "options"
        );

    optionsContainer.innerHTML = "";


    data.question.options.forEach(
        option => {

            const button =
                document.createElement(
                    "button"
                );

            button.className = "option";

            button.textContent = option;

            button.onclick = function () {

                submitAnswer(option);

            };

            optionsContainer.appendChild(
                button
            );
        }
    );


    showScreen("quiz-screen");
}


function updateTeamTimer(seconds) {

    document.getElementById(
        "team-timer"
    ).textContent = seconds;


    if (
        seconds <= 0 &&
        !hasAnswered
    ) {

        const buttons =
            document.querySelectorAll(
                ".option"
            );

        buttons.forEach(
            button => {
                button.disabled = true;
            }
        );

        document.getElementById(
            "answer-message"
        ).textContent =
            "Time's up!";
    }
}


async function submitAnswer(answer) {

    if (hasAnswered) {
        return;
    }

    if (!currentQuestionData) {
        return;
    }

    hasAnswered = true;


    const buttons =
        document.querySelectorAll(
            ".option"
        );

    buttons.forEach(
        button => {
            button.disabled = true;
        }
    );


    try {

        const response =
            await fetch("/answer", {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({

                    team_id: teamId,

                    question_id:
                        currentQuestionData.id,

                    answer: answer
                })
            });


        const data =
            await response.json();


        if (!data.success) {

            hasAnswered = false;

            document.getElementById(
                "answer-message"
            ).textContent =
                data.message;

            return;
        }


        document.getElementById(
            "answer-result"
        ).textContent =
            data.correct
                ? "Correct!"
                : "Wrong Answer";


        document.getElementById(
            "answer-score"
        ).textContent =
            `+${data.points} points • Total Score: ${data.score}`;


        showScreen("answered-screen");

    } catch (error) {

        hasAnswered = false;

        console.error(error);

        document.getElementById(
            "answer-message"
        ).textContent =
            "Connection error.";
    }
}


function showScreen(screenId) {

    const screens = [
        "register-screen",
        "waiting-screen",
        "quiz-screen",
        "answered-screen",
        "finished-screen"
    ];


    screens.forEach(id => {

        const element =
            document.getElementById(id);

        if (element) {

            element.classList.add("hidden");
        }

    });


    const target =
        document.getElementById(screenId);

    if (target) {

        target.classList.remove("hidden");
    }
}