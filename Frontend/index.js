// Amikor egy játék elkészül, a "page" mezőjébe be kell írni az oldalának nevét.
const games = [
  {
    id: "tictactoe",
    name: "Amőba",
    description: "Rakj egymás mellé három (5×5-ös táblán négy) jelet. Játszhatsz a gép ellen vagy ketten egy gépen.",
    page: "tictactoe.html",
  },
  {
    id: "hangman",
    name: "Akasztófa",
    description: "Találd ki a szót, mielőtt elfogynak a próbálkozásaid.",
    page: null,
  },
  {
    id: "typing",
    name: "Gépelős játék",
    description: "Írd be a szöveget minél gyorsabban és pontosabban.",
    page: null,
  },
  {
    id: "memory",
    name: "Memóriajáték",
    description: "Találd meg a kártyapárokat minél kevesebb hibával.",
    page: null,
  },
  {
    id: "number",
    name: "Számkitaláló",
    description: "Találd ki a gondolt számot minél kevesebb tippből.",
    page: null,
  },
];

const errorEl = document.getElementById("error");
const gamesEl = document.getElementById("games");


function renderGames() {
  for (const game of games) {
    const box = document.createElement("div");
    box.className = "game";

    const title = document.createElement("h2");
    title.textContent = game.name;
    box.appendChild(title);

    const description = document.createElement("p");
    description.textContent = game.description;
    box.appendChild(description);

    if (game.page === null) {
      box.classList.add("soon");
      const soon = document.createElement("p");
      soon.textContent = "Hamarosan.";
      box.appendChild(soon);
    } else {
      const link = document.createElement("a");
      link.className = "play-link";
      link.href = game.page;
      link.textContent = "Játék";
      box.appendChild(link);

      const top3Title = document.createElement("h3");
      top3Title.textContent = "Top 3";
      box.appendChild(top3Title);

      const top3 = document.createElement("div");
      box.appendChild(top3);
      showTop3(game.id, top3);
    }

    gamesEl.appendChild(box);
  }
}

async function init() {
  const me = await showUser();
  if (!me.ok) {
    if (me.status === 0) {
      errorEl.textContent = "A szerver nem érhető el.";
      errorEl.hidden = false;
    }
    return;
  }
  // TODO: admin hivatkozás, ha lesz admin oldal (me.data.role === "admin")
  renderGames();
}

document.getElementById("logout-btn").addEventListener("click", logout);

init();
