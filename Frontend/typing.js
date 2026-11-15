let round = null;
let timerId = null;
let busy = false;

const modeSelect = document.getElementById("mode");
const difficultySelect = document.getElementById("difficulty");
const difficultyBox = document.getElementById("difficulty-box");
const messageEl = document.getElementById("message");
const gameEl = document.getElementById("game");
const textEl = document.getElementById("text");
const inputEl = document.getElementById("typing-input");
const playerBar = document.getElementById("player-bar");
const playerCount = document.getElementById("player-count");
const botRow = document.getElementById("bot-row");
const botBar = document.getElementById("bot-bar");
const botCount = document.getElementById("bot-count");
const errorEl = document.getElementById("error");
const resultEl = document.getElementById("result");
const resultTextEl = document.getElementById("result-text");
const top3El = document.getElementById("top3");

let charSpans = [];

function errorText(status, data) {
  const serverText = data && typeof data.error === "string" ? data.error : "";

  if (status === 0) return "A szerver nem érhető el.";
  if (status === 503) return "Jelenleg nincs elérhető tartalom ehhez a játékhoz.";
  if (status === 404) return "Nincs folyamatban lévő játék.";
  if (status === 409) return "A játék véget ért. Indíts új játékot.";
  if (status === 400) {
    if (serverText.includes("kör nem számít")) return "Az eredmény érvénytelen, a kör nem számít.";
    return "Érvénytelen kérés.";
  }
  return "Ismeretlen hiba történt. Próbáld újra.";
}

function showError(text) {
  errorEl.textContent = text;
  errorEl.hidden = false;
}

function clearError() {
  errorEl.textContent = "";
  errorEl.hidden = true;
}




function buildText(text) {
  textEl.innerHTML = "";
  charSpans = [];
  for (const char of text) {
    const span = document.createElement("span");
    span.textContent = char;
    textEl.appendChild(span);
    charSpans.push(span);
  }
}

function colorText(typed) {
  const text = round.text;
  for (let i = 0; i < charSpans.length; i++) {
    if (i < typed.length) {
      charSpans[i].className = typed[i] === text[i] ? "ok" : "bad";
    }
    else if (i === typed.length) {
      charSpans[i].className = "current";
    }
    else {
      charSpans[i].classname = "";
    }
  }
}

function updateProgress() {
  if (round === null) return;
  const total = round.text.length;
  const typedCount = inputEl.value.length;

  playerBar.style.width = (typedCount / total) * 100 + "%";
  playerCount.textContent = typedCount + " / " + total;

  if (round.botWpm !== null) {
    const minutes = (performance.now() - round.startedAt) / 60000;
    const botChars = Math.min(total, Math.floor(round.botWpm * 5 * minutes))
    botBar.style.width = (botChars / total) * 100 + "%";
    botCount.textContent = botChars + " / " + total;
  }
}

function stopTimer() {
  if (timerId !== null) {
    clearInterval(timerId)
    timerId = null;
  }
}

function updateDifficultyBox() {
  difficultyBox.hidden = modeSelect.value !== "bot";
}

function showResult(data) {
  if (data.winner === "player") {
    resultTextEl.textContent = "Te nyertél!";
  }
  else if (data.winner === "bot") {
    resultTextEl.textContent = "A gép nyert!";
  }
  else {
    resultTextEl.textContent = "Kész a gyakorlókör.";
  }

  document.getElementById("r-time").textContent = data.elapsed_seconds + " mp";
  document.getElementById("r-wpm").textContent = data.wpm + " szó/perc";
  document.getElementById("r-accuracy").textContent = Math.round(data.accuracy * 100) + "%";
  document.getElementById("r-points").textContent = data.points;
  resultEl.hidden = false;
}

function loadTop3() {
  return showTop3("typing", top3El);
}



async function startRound() {
  if (busy) return;
  busy = true;
  stopTimer();
  clearError();
  resultEl.hidden = true;

  const body = { mode: modeSelect.value };
  if (modeSelect.value === "bot") body.difficulty = difficultySelect.value;
  const result = await api("/typing/start", "POST", body);
  busy = false;

  if (!result.ok) {
    round = null;
    gameEl.hidden = true;
    messageEl.textContent = "";
    showError(errorText(result.status, result.data));
    return;
  }

  round = {
    sessionId: result.data.session_id,
    text: result.data.text,
    botWpm: result.data.bot_wpm === undefined ? null : result.data.bot_wpm,
    startedAt: performance.now(),
  };

  buildText(round.text);
  botRow.hidden = round.botWpm === null;
  botBar.style.width = "0%";
  inputEl.value = "";
  inputEl.maxLength = round.text.length;
  inputEl.disabled = false;
  gameEl.hidden = false;
  colorText("");
  updateProgress();
  timerId = setInterval(updateProgress, 100);
  inputEl.focus();
  messageEl.textContent = round.botWpm === null ?
    "Gépelj! az idő már megy." : "Gépelj, mielőtt a gép végez! Az idő már megy.";
}

async function sendResult(typed) {
  const sessionId = round.sessionId;
  inputEl.disabled = true;
  stopTimer();
  messageEl.textContent = "Kiértékelés...";

  const result = await api("/typing/finish", "POST", { session_id: sessionId, typed_text: typed });
  round = null;
  messageEl.textContent = "A kör véget ért.";

  if (!result.ok) {
    showError(errorText(result.status, result.data));
    return;
  }
  showResult(result.data);
  loadTop3();
}




inputEl.addEventListener("input", function () {
  if (round === null) return;
  colorText(inputEl.value);
  updateProgress();
  if (inputEl.value.length >= round.text.length) {
    sendResult(inputEl.value);
  }
});

inputEl.addEventListener("paste", function (event) {
  event.preventDefault();
});
inputEl.addEventListener("drop", function (event) {
  event.preventDefault();
});

document.getElementById("new-round-btn").addEventListener("click", startRound);
document.getElementById("again-btn").addEventListener("click", startRound);
document.getElementById("logout-btn").addEventListener("click", logout);
modeSelect.addEventListener("change", updateDifficultyBox);



async function init() {
  updateDifficultyBox();
  const me = await showUser();
  if (!me.ok) {
    if (me.status === 0) showError(errorText(0, null));
    return;
  }
  messageEl.textContent = "Válassz módot és kattints az Új kör gombra.";
  loadTop3();
}

init();
