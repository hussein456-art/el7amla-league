// ============================================
// El7amla League — Shared JS Helpers
// Loaded by every page. One place for the logic
// that used to be copy-pasted across HTML files.
// ============================================

// Prevents XSS: never insert a team/player name into
// innerHTML without passing it through this first.
function escapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// Fetches JSON with a cache-busting query param so the
// browser always grabs the latest saved version.
async function fetchJSON(path) {
  const res = await fetch(`${path}?v=${Date.now()}`);
  if (!res.ok) throw new Error(`HTTP ${res.status} — ${path}`);
  return res.json();
}

// Loads data/teams-config.json once and returns a lookup
// object keyed by team name: { "Boys": { color, emoji }, ... }
let _teamsConfigCache = null;
async function getTeamsConfig() {
  if (_teamsConfigCache) return _teamsConfigCache;
  const data = await fetchJSON('data/teams-config.json');
  _teamsConfigCache = {};
  data.teams.forEach(t => { _teamsConfigCache[t.name] = t; });
  return _teamsConfigCache;
}

// Renders the team standings table into any container element.
async function renderStandingsTable(containerId) {
  const el = document.getElementById(containerId);
  try {
    const [standings, teamsConfig] = await Promise.all([
      fetchJSON('data/standings.json'),
      getTeamsConfig(),
    ]);

    const sorted = [...standings.teams].sort((a, b) => b.total - a.total);

    const rows = sorted.map((t, i) => {
      const meta = teamsConfig[t.name] || { color: '#64748b', emoji: '⚽' };
      return `
        <tr>
          <td>${i + 1}</td>
          <td style="color:${meta.color}">${meta.emoji} ${escapeHtml(t.name)}</td>
          <td>${t.played}</td>
          <td>${t.won}</td>
          <td>${t.draw}</td>
          <td>${t.lost}</td>
          <td class="pts-total">${t.total}</td>
        </tr>`;
    }).join('');

    el.innerHTML = `
      <table>
        <thead><tr>
          <th>المركز</th><th>الفريق</th><th>لعب</th><th>فوز</th><th>تعادل</th><th>خسارة</th><th>النقاط</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  } catch (err) {
    console.error(err);
    el.innerHTML = `<div class="state-box">⚠️ فشل تحميل البيانات</div>`;
  }
}

// Renders a simple card grid of teams + their players.
async function renderTeamsGrid(containerId) {
  const el = document.getElementById(containerId);
  try {
    const [league, teamsConfig] = await Promise.all([
      fetchJSON('data/league.json'),
      getTeamsConfig(),
    ]);

    const cards = Object.entries(league.teams).map(([teamName, teamData]) => {
      const meta = teamsConfig[teamName] || { color: '#64748b', emoji: '⚽' };
      const playersHtml = teamData.players
        .map(p => `<li>${escapeHtml(p.name)}</li>`)
        .join('');

      return `
        <div class="team-card" style="border-color:${meta.color}">
          <div class="team-card-header" style="color:${meta.color}">
            <span>${meta.emoji}</span> ${escapeHtml(teamName)}
          </div>
          <ul class="team-card-players">${playersHtml}</ul>
        </div>`;
    }).join('');

    el.innerHTML = `<div class="teams-grid">${cards}</div>`;
  } catch (err) {
    console.error(err);
    el.innerHTML = `<div class="state-box">⚠️ فشل تحميل البيانات</div>`;
  }
}

// Renders all gameweeks + their matches.
async function renderFixtures(containerId) {
  const el = document.getElementById(containerId);
  try {
    const [fixtures, teamsConfig] = await Promise.all([
      fetchJSON('data/fixtures.json'),
      getTeamsConfig(),
    ]);

    const teamLabel = (name) => {
      const meta = teamsConfig[name] || { color: '#64748b', emoji: '⚽' };
      return `<span style="color:${meta.color}">${meta.emoji} ${escapeHtml(name)}</span>`;
    };

    const blocks = fixtures.fixtures.map(gwBlock => {
      const matchesHtml = gwBlock.matches.map(([home, away]) => `
        <div class="fixture-row">
          <span class="fixture-team">${teamLabel(home)}</span>
          <span class="fixture-vs">ضد</span>
          <span class="fixture-team">${teamLabel(away)}</span>
        </div>`).join('');

      return `
        <div class="gw-block">
          <div class="gw-title">الجولة ${gwBlock.gw}</div>
          ${matchesHtml}
        </div>`;
    }).join('');

    el.innerHTML = blocks;
  } catch (err) {
    console.error(err);
    el.innerHTML = `<div class="state-box">⚠️ فشل تحميل البيانات</div>`;
  }
}
