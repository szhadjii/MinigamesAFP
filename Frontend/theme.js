function currentTheme() {
  try {
    const saved = localStorage.getItem("theme");
    if (saved === "dark" || saved === "light") return saved;
  }
  catch (e) { }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  const button = document.getElementById("theme-btn");
  if (button) button.textContent = theme === "dark" ? "Világos mód" : "Sötét mód";
}

function toggleTheme() {
  const next = currentTheme() === "dark" ? "light" : "dark";
  try {
    localStorage.setItem("theme", next);
  }
  catch (e) { }
  document.documentElement.setAttribute("data-theme", next);
  applyTheme(next);
}

applyTheme(currentTheme());

document.addEventListener("DOMContentLoaded", function () {
  applyTheme(document.documentElement.getAttribute("data-theme"));
  const button = document.getElementById("theme-btn");
  if (button) button.addEventListener("click", toggleTheme);
});
