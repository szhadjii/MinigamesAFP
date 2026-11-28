let sessionId = null;
const hungarianAlphabet = "AÁBCDEÉFGHIÍJKLMNOÓÖŐPQRSTUÚÜŰVWXYZ";
const API_BASE = "http://localhost:5000/api/hangman"; // Ha a Flask más porton fut, írd át!

async function startGame() {
    document.getElementById('game-content').style.display = 'block';
    document.getElementById('start-btn').style.display = 'none';
    document.getElementById('message').textContent = 'Szó generálása...';
    document.getElementById('message').style.color = '#69E3CC';

    const difficulty = document.getElementById('difficulty').value;

    try {
        const res = await fetch(`${API_BASE}/start?difficulty=${difficulty}`, { method: 'POST' });
        const data = await res.json();

        if (!res.ok) throw new Error(data.error || 'Hiba a játék indításakor.');

        sessionId = data.sessionId;
        document.getElementById('hint').textContent = `💡 Tipp: ${data.hint}`;
        document.getElementById('mistakes').textContent = `Hibák: 0 / ${data.maxMistakes}`;
        document.getElementById('word-display').textContent = "_ ".repeat(data.wordLength).trim();
        document.getElementById('keyboard').innerHTML = ''; // Töröljük a régit
        
        renderKeyboard();
        document.getElementById('message').textContent = 'Válassz egy betűt!';
        document.getElementById('message').style.color = '#69E3CC';
    } catch (e) {
        document.getElementById('message').textContent = e.message;
        document.getElementById('message').style.color = '#F04747';
        document.getElementById('start-btn').style.display = 'inline-block';
    }
}

function renderKeyboard() {
    const kb = document.getElementById('keyboard');
    for (const ch of hungarianAlphabet) {
        const btn = document.createElement('button');
        btn.className = 'key';
        btn.textContent = ch;
        btn.onclick = () => guess(ch, btn);
        kb.appendChild(btn);
    }
}

async function guess(letter, btn) {
    if (!sessionId) return;
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/guess?sessionId=${sessionId}&letter=${letter}`, {
            method: 'POST'
        });
        const data = await res.json();

        btn.classList.add(data.message.includes('Helyes') ? 'correct' : 'wrong');
        
        if (data.display) {
            document.getElementById('word-display').textContent = data.display.split('').join(' ').trim();
            document.getElementById('mistakes').textContent = `Hibák: ${data.mistakes} / ${data.maxMistakes}`;
            
            const msgEl = document.getElementById('message');
            msgEl.textContent = data.message;
            msgEl.style.color = data.message.includes('Helyes') ? '#69E3CC' : '#F04747';

            if (data.finished) {
                msgEl.textContent = data.won ? '🎉 Nyertél!' : '💀 Vesztettél!';
                msgEl.style.color = data.won ? '#43B581' : '#F04747';
                document.querySelectorAll('.key').forEach(b => b.disabled = true);
                document.getElementById('start-btn').style.display = 'inline-block';
                document.getElementById('start-btn').textContent = 'Új játék';
            }
        }
    } catch (e) {
        document.getElementById('message').textContent = 'Hiba történt a tippelés során.';
        document.getElementById('message').style.color = '#F04747';
    }
}