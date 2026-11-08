let game = null;
let lastAIMove = null;
let busy = false;

const COUNTER_KEY = "tictactoe_counter";

const modeSelect = document.getElementById("mode");
const sizeSelect = document.getElementById("size");
const difficultySelect = document.getElementById("difficulty");
const difficultyBox = document.getElementById("difficulty-box");
const messageEl = document.getElementById("message");
const counterEl = document.getElementById("counter");
const boardEl = document.getElementById("board");
const errorEl = document.getElementById("error");
const resultEl = document.getElementById("result");
const resultTextEl = document.getElementById("result-text");
const top3El = document.getElementById("top3");

// Hibaüzenetek ------------------------------------------------

function serverMessage(result) {
  const d = result.data;
  if (!d) return "";
  return d.error || d.message || d.msg || d.detail || "";
}

function errorText(status, serverText) {
  serverText = serverText || ""
  switch (status) {
    case 0:
      return "A szerver nem érhető el.";
    case 404:
      return "Nincs folyamatban lévő játék.";
    case 400:
      return "Érvénytelen kérés.";
    case 409:
      if (serverText.includes("foglalt")) return "Ez a mező már foglalt.";
      if (serverText.includes("véget ért")) return "A játék véget ért. Indíts új játékot.";
      if (serverText.includes("aktív játék")) return "Nincs folyamatban lévő játék.";
      return serverText || "A kérés most nem hajtható végre.";
    default:
      return "Ismeretlen hiba történt. Próbáld újra.";
  }
}

function showError(text) {
  errorEl.textContent = text;
  errorEl.hidden = false;
}

function clearError() {
  errorEl.textContent = "";
  errorEl.hidden = true;
}


function readCounter() {
  try {
    const saved = sessionStorage.getItem(COUNTER_KEY);
    return saved ? JSON.parse(saved) : { x: 0, o: 0, draw: 0 };
  }
  catch (e) {
    return null;
  }
}

function addToCounter(status) {
  const counter = readCounter();
  if (counter === null) return;
  if (status === "X won!") counter.x++;
  else if (status === "O won!") counter.o++;
  else counter.draw++;
  try {
    sessionStorage.setItem(COUNTER_KEY, JSON.stringify(counter));
  }
  catch (e) { }
}

function renderCounter() {
  const counter = readCounter();
  if (game === null || game.mode !== "two_player" || counter === null) {
    counterEl.textContent = "";
    return;
  }
  counterEl.textContent = "Győzelmek - X: " + counter.x + ", O: " + counter.o + ", Döntetlen: " + counter.draw;
}

// Render, megjelenítés
function renderBoard() {
  if (game === null) {
    boardEl.hidden = true;
    return
  }

  const size = game.size
  const finished = game.status !== "in progress";
  boardEl.className = "board size" + size;
  boardEl.innerHTML = "";

  for (let row = 0; row < size; row++){
    for (let column = 0; column < size; column++){
      const value = game.table[row][column];
      const cell = document.createElement("button")
      cell.type = "button";
      cell.className = "cell";
      cell.textContent = value;
      cell.dataset.row = row;
      cell.dataset.column = column;
      cell.setAttribute("aria-label", (row + 1) + ". sor, " + (column + 1) + ". oszlop");

      if (value === "X") cell.classList.add("x");
      if (value === "O") cell.classList.add("o");
      if (lastAIMove && lastAIMove[0] === row && lastAIMove[1] === column) {
        cell.classList.add("ai-move");
      }
      for (const field of game.winning_fields) {
        if (field[0] === row && field[1] === column) cell.classList.add("win");
      }
      if (finished) cell.disabled = true;

      boardEl.appendChild(cell);
    }
  }
  boardEl.hidden = false;
}

function renderStatus() {
  if (game === null) {
    messageEl.textContent = "Válassz beállításokat, és kattints az Új játék gombra.";
    resultEl.hidden = true;
    return;
  }

  if (game.status === "in progress") {
    if (game.mode === "ai") {
      messageEl.textContent = "Te jössz (X).";
    }
    else {
      messageEl.textContent = "Következik: " + game.next;
    }
    resultEl.hidden = true;
    return;
  }

  messageEl.textContent = "A játék véget ért.";
  if (game.mode === "ai") {
    if (game.status === "X won!") resultTextEl.textContent = "Nyertél! Pont: " + game.points;
    else if (game.status === "O won!") resultTextEl.textContent = "A gép nyert. Pont: " + game.points
    else resultTextEl.textContent = "Döntetlen. Pont: " + game.points;
  }
  else {
    if (game.status === "X won!") resultTextEl.textContent = "X nyert!";
    else if (game.status === "O won!") resultTextEl.textContent = "O nyert!";
    else resultTextEl.textContent = "Döntetlen!";
  }
  resultEl.hidden = false;
}

function render() {
  renderBoard();
  renderStatus();
  renderCounter();
}

function updateDifficultyBox() {
  difficultyBox.hidden = modeSelect.value !== "ai";
}

function loadSettingsFromGame() {
  modeSelect.value = game.mode;
  sizeSelect.value = String(game.size);
  if (game.difficulty) difficultySelect.value = game.difficulty;
  updateDifficultyBox();
}

function loadTop3() {
  return showTop3("tictactoe", top3El);
}


async function startGame(mode, size, difficulty) {
  if (busy) return;
  busy = true;
  const body = { mode: mode, size: Number(size) };
  if (mode === "ai") body.difficulty = difficulty;
  const result = await api("/tictactoe/new-game", "POST", body);
  busy = false;

  if (!result.ok) {
    showError(errorText(result.status, serverMessage(result)));
    return;
  }
  game = result.data;
  lastAIMove = null;
  clearError();
  render();
}

async function makeMove(row, column) {
  if (busy) return;
  busy = true;

  const result = await api("/tictactoe/turn", "POST", { row: row, column: column });
  busy = false;

  if (!result.ok) {
    showError(errorText(result.status, serverMessage(result)));
    return;
  }
  game = result.data;
  lastAIMove = game.ai_move;
  clearError();

  const finished = game.status !== "in progress";
  if (finished && game.mode === "two_player") addToCounter(game.status);
  render();
  if (finished && game.mode === "ai") loadTop3();
}

async function loadState() {
  const result = await api("/tictactoe/state");
  if (result.ok) {
    game = result.data;
    loadSettingsFromGame();
  }
  else if (result.status === 404) {
    game = null
  }
  else {
    showError(errorText(result.status, serverMessage(result)));
  }
  render();
}


// Eseménykezelők ----------------------------------------------------------

boardEl.addEventListener("click", function (event) {
  const cell = event.target.closest(".cell");
  if (cell === null || cell.disabled) return;
  makeMove(Number(cell.dataset.row), Number(cell.dataset.column));
});

document.getElementById("new-game-btn").addEventListener("click", function () {
  startGame(modeSelect.value, sizeSelect.value, difficultySelect.value);
});

document.getElementById("replay-btn").addEventListener("click", function () {
  startGame(game.mode, game.size, game.difficulty);
});

document.getElementById("logout-btn").addEventListener("click", logout);
modeSelect.addEventListener("change", updateDifficultyBox);

// Init -----------------------------------------------------------------------

async function init() {
  updateDifficultyBox();
  const user = await showUser();
  if (!user.ok) {
    if (user.status === 0) showError(errorText(0, ""));
    return;
  }
  await loadState();
  await loadTop3();
}

init();
