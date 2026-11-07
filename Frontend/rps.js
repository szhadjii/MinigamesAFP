// Kő-papír-olló felülete. A script.js után töltődik be, és a GAME_UI-ba regisztrálja magát.
GAME_UI.rps = (box, game, done) => {
  const area = h('div');
  box.append(area);
  const MOVES = [['rock', '🪨', 'Kő'], ['paper', '📄', 'Papír'], ['scissors', '✂️', 'Olló']];
  const icon = m => MOVES.find(x => x[0] === m)[1];
  const OUT = { win: 'Nyertél!', draw: 'Döntetlen.', loss: 'Vesztettél.' };

  async function newGame() {
    try { render(await api('/rps/start', 'POST')); }
    catch (e) { area.replaceChildren(h('div', { className: 'msg', textContent: e.message }), b('Újra', newGame)); }
  }

  const line = x => h('div', { textContent: 'Te: ' + icon(x.player) + '  Gép: ' + icon(x.computer) + ' – ' + OUT[x.outcome] });

  function render(s, last) {
    const info = h('div', { className: 'msg' + (last && last.outcome !== 'loss' ? ' ok' : ''),
                            textContent: last ? OUT[last.outcome] + (last.gained ? ' +' + last.gained + ' pont' : '') : '' });
    const buttons = h('div', { className: 'row' }, MOVES.map(([key, ico, name]) =>
      b(ico + ' ' + name, () => play(key, buttons, info))));
    area.replaceChildren(
      h('p', { textContent: '5 körös meccs. Győzelem: 10 pont, döntetlen: 3 pont.' }),
      h('div', { className: 'big', textContent: 'Kör: ' + Math.min(s.round + 1, s.total) + '/' + s.total + ' · Pontok: ' + s.score }),
      buttons, info,
      h('div', { className: 'muted' }, s.history.map(line)));
  }

  async function play(move, buttons, info) {
    [...buttons.children].forEach(x => x.disabled = true);
    try {
      const r = await api('/rps/play', 'POST', { move });
      if (r.finished) return finish(r);
      render(await api('/rps/current'), r);
    } catch (e) {
      [...buttons.children].forEach(x => x.disabled = false);
      info.className = 'msg'; info.textContent = e.message;
    }
  }

  function finish(r) {
    area.replaceChildren(
      h('div', { className: 'big', textContent: 'Utolsó kör – Te: ' + icon(r.player) + '  Gép: ' + icon(r.computer) + ' – ' + OUT[r.outcome] }),
      h('p', { textContent: 'Győzelem: ' + r.stats.win + ' · Döntetlen: ' + r.stats.draw + ' · Vereség: ' + r.stats.loss }),
      h('p', { className: 'msg' + (r.points > 0 ? ' ok' : ''), textContent: 'Játék vége! +' + r.points + ' pont' }),
      b('Új meccs', newGame));
    done();
  }

  // Ha van félbehagyott meccs, folytatjuk, különben újat indítunk.
  api('/rps/current').then(s => render(s)).catch(newGame);
};
