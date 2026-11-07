let redirectOn401 = true;

async function api(url, method = "GET", body = null) {
  const options = { method: method, headers: {} };
  if (body !== null) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(url, options);
    let data = null;
    try {
      data = await response.json();
    } catch (e) {
      // nem JSON a válasz
    }
    if (response.status === 401 && redirectOn401) {
      window.location.href = "login.html"; // nincs bejelentkezve
    }
    return { ok: response.ok, status: response.status, data: data };
  } catch (e) {
    return { ok: false, status: 0, data: null };
  }
}


async function showUser() {
  const result = await api("/auth/me");
  if (result.ok) {
    document.getElementById("username").textContent = result.data.username || "";
  }
  return result;
}

async function logout() {
  await api("/auth/logout", "POST");
  window.location.href = "login.html";
}


async function showTop3(gameId, element, difficulty = null) {
  let url = "/scores/top?game=" + gameId;
  if (difficulty !== null) url += "&difficulty=" + difficulty;
  const result = await api(url);
  element.innerHTML = "";

  if (!result.ok) {
    element.textContent = "A lista nem tölthető be.";
    return;
  }
  if (result.data.length === 0) {
    element.textContent = "Még nincs eredmény.";
    return;
  }

  const list = document.createElement("ol");
  for (const entry of result.data) {
    const item = document.createElement("li");
    item.textContent = entry.username + " – " + entry.points + " pont";
    list.appendChild(item);
  }
  element.appendChild(list);
}
