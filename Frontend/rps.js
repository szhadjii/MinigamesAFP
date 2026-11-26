// Kő-papír-olló oldal. A gép lépését és az eredményt a szerver állapítja meg,
// ez a fájl csak elküldi a választást és megjeleníti a meccs állását.

let match = null;   // a meccs állása a szervertől: {round, total, score, history}, null ha nincs meccs
let busy = false;   // kérés közben ne lehessen újra kattintani

const MOVE_NAMES = { rock: "Kő", paper: "Papír", scissors: "Olló" };
const OUTCOME_NAMES = { win: "Nyertél", draw: "Döntetlen", loss: "Vesztettél" };

const startBox = document.getElementById("start-box");
const matchEl = document.getElementById("match");
const statusEl = document.getElementById("status");
const movesEl = document.getElementById("moves");
const lastRoundEl = document.getElementById("last-round");
const historyEl = document.getElementById("history");
const errorEl = document.getElementById("error");
const resultEl = document.getElementById("result");
const resultTextEl = document.getElementById("result-text");
const resultStatsEl = document.getElementById("result-stats");
const top3El = document.getElementById("top3");


// ---------- Hibaüzenetek ----------

function errorText(status, data) {
  const serverText = data && typeof data.error === "string" ? data.error : "";

  if (status === 0) return "A szerver nem érhető el.";
  if (status === 404) return "Nincs folyamatban lévő játék.";
  if (status === 400) return "Érvénytelen kérés.";
  if (status === 409) return serverText || "A kérés most nem hajtható végre.";
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


// ---------- Megjelenítés ----------

function lastRoundText(entry, gained) {
  let text = "Te: " + MOVE_NAMES[entry.player] + " · Gép: " + MOVE_NAMES[entry.computer] +
    " – " + OUTCOME_NAMES[entry.outcome] + ".";
  if (gained > 0) text += " +" + gained + " pont";
  return text;
}

function renderHistory() {
  historyEl.innerHTML = "";
  match.history.forEach(function (entry, index) {
    const row = document.createElement("tr");

    const cells = [index + 1, MOVE_NAMES[entry.player], MOVE_NAMES[entry.computer], OUTCOME_NAMES[entry.outcome]];
    cells.forEach(function (content, position) {
      const cell = document.createElement("td");
      cell.textContent = content;
      if (position === 3 && entry.outcome !== "draw") cell.className = entry.outcome;
      row.appendChild(cell);
    });
    historyEl.appendChild(row);
  });
}

function renderMatch() {
  if (match === null) {
    matchEl.hidden = true;
    startBox.hidden = false;
    return;
  }

  startBox.hidden = true;
  matchEl.hidden = false;

  if (match.finished) {
    statusEl.textContent = "A meccs véget ért · Pontok: " + match.score;
  } else {
    const round = Math.min(match.round + 1, match.total);
    statusEl.textContent = "Kör: " + round + "/" + match.total + " · Pontok: " + match.score;
  }

  for (const button of movesEl.children) {
    button.disabled = match.finished === true;
  }
  renderHistory();
}

function showFinish(data) {
  const stats = data.stats;
  resultTextEl.textContent = "A meccs véget ért! Megszerzett pont: " + data.points;
  resultStatsEl.textContent =
    "Győzelem: " + stats.win + " · Döntetlen: " + stats.draw + " · Vereség: " + stats.loss;
  resultEl.hidden = false;
}

function loadTop3() {
  return showTop3("rps", top3El);
}


// ---------- Műveletek ----------

async function startMatch() {
  if (busy) return;
  busy = true;
  clearError();
  resultEl.hidden = true;
  lastRoundEl.textContent = "";

  const result = await api("/rps/start", "POST");
  busy = false;

  if (!result.ok) {
    showError(errorText(result.status, result.data));
    return;
  }
  match = result.data;
  renderMatch();
}

async function playMove(move) {
  if (busy || match === null || match.finished) return;
  busy = true;
  clearError();

  const result = await api("/rps/play", "POST", { move: move });
  busy = false;

  if (!result.ok) {
    showError(errorText(result.status, result.data));
    return;
  }

  // A szerver csak az aktuális kört adja vissza, a korábbiakat mi tartjuk a listában
  const data = result.data;
  const entry = { player: data.player, computer: data.computer, outcome: data.outcome };
  match = {
    round: data.round,
    total: data.total,
    score: data.score,
    history: match.history.concat([entry]),
    finished: data.finished,
  };
  lastRoundEl.textContent = lastRoundText(entry, data.gained);
  renderMatch();

  if (data.finished) {
    showFinish(data);
    loadTop3();
  }
}

// Ha van félbehagyott meccs, folytatjuk, különben az indítóképernyő látszik
async function loadCurrent() {
  const result = await api("/rps/current");
  if (result.ok) {
    match = result.data;
    renderMatch();
    lastRoundEl.textContent = "Folytatod a félbehagyott meccset.";
  } else if (result.status === 404) {
    match = null;
    renderMatch();
  } else {
    showError(errorText(result.status, result.data));
  }
}


// ---------- Eseménykezelők ----------

movesEl.addEventListener("click", function (event) {
  const button = event.target.closest("button");
  if (button === null || button.disabled) return;
  playMove(button.dataset.move);
});

document.getElementById("new-match-btn").addEventListener("click", startMatch);
document.getElementById("again-btn").addEventListener("click", startMatch);
document.getElementById("logout-btn").addEventListener("click", logout);


// ---------- Indulás ----------

async function init() {
  const me = await showUser();
  if (!me.ok) {
    if (me.status === 0) showError(errorText(0, null));
    return; // 401-nél a common.js már átirányított a bejelentkezésre
  }
  await loadCurrent();
  loadTop3();
}

init();
