const MIN_USERNAME = 3;
const MAX_USERNAME = 20;
const MIN_PASSWORD = 8;

redirectOn401 = false;

const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const loginInfo = document.getElementById("login-info");
const loginError = document.getElementById("login-error");
const registerError = document.getElementById("register-error");


function showMessage(element, text) {
  element.textContent = text;
  element.hidden = false;
}

function hideMessages() {
  for (const element of [loginInfo, loginError, registerError]) {
    element.textContent = "";
    element.hidden = true;
  }
}

function loginErrorText(status) {
  if (status === 0) return "A szerver nem érhető el.";
  if (status === 401) return "Hibás felhasználónév vagy jelszó.";
  if (status === 403) return "A fiók le van tiltva.";
  if (status === 400) return "A felhasználónév vagy a jelszó nem megfelelő.";
  return "Ismeretlen hiba történt. Próbáld újra.";
}

function registerErrorText(status) {
  if (status === 0) return "A szerver nem érhető el.";
  if (status === 409) return "Ez a felhasználónév már foglalt.";
  if (status === 400) return "A felhasználónév vagy a jelszó nem megfelelő.";
  return "Ismeretlen hiba történt. Próbáld újra.";
}


async function login(event) {
  event.preventDefault();
  hideMessages();

  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value;
  if (username === "" || password === "") {
    showMessage(loginError, "Add meg a felhasználónevet és a jelszót.");
    return;
  }

  const result = await api("/auth/login", "POST", { username: username, password: password });
  if (!result.ok) {
    showMessage(loginError, loginErrorText(result.status));
    return;
  }
  window.location.href = "/";
}

async function register(event) {
  event.preventDefault();
  hideMessages();

  const username = document.getElementById("register-username").value.trim();
  const password = document.getElementById("register-password").value;
  const password2 = document.getElementById("register-password2").value;

  if (username.length < MIN_USERNAME || username.length > MAX_USERNAME) {
    showMessage(registerError, "A felhasználónév " + MIN_USERNAME + "–" + MAX_USERNAME + " karakter legyen.");
    return;
  }
  if (password.length < MIN_PASSWORD) {
    showMessage(registerError, "A jelszó legalább " + MIN_PASSWORD + " karakter legyen.");
    return;
  }
  if (password !== password2) {
    showMessage(registerError, "A két jelszó nem egyezik.");
    return;
  }

  const result = await api("/auth/register", "POST", { username: username, password: password });
  if (!result.ok) {
    showMessage(registerError, registerErrorText(result.status));
    return;
  }

  registerForm.reset();
  document.getElementById("login-username").value = username;
  document.getElementById("login-password").value = "";
  document.getElementById("login-password").focus();
  showMessage(loginInfo, "Sikeres regisztráció. Most jelentkezz be.");
}


loginForm.addEventListener("submit", login);
registerForm.addEventListener("submit", register);

async function checkLoggedIn() {
  const result = await api("/auth/me");
  if (result.ok) window.location.href = "/";
}

checkLoggedIn();
