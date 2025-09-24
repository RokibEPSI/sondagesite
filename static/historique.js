let allPolls = [];

async function loadHistorique() {
  let res = await fetch("/api/polls/expired");
  allPolls = await res.json();
  renderPolls();
}

function renderPolls() {
  let container = document.getElementById("historique-list");
  container.innerHTML = "";

  let search = document.getElementById("searchInput").value.toLowerCase();
  let filtered = allPolls.filter(p => p.question.toLowerCase().includes(search));

  let sortType = document.getElementById("sortSelect").value;
  if (sortType === "recent") {
    filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  } else if (sortType === "old") {
    filtered.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
  } else if (sortType === "popular") {
    filtered.sort((a, b) => {
      let votesA = a.options.reduce((sum, opt) => sum + opt.votes, 0);
      let votesB = b.options.reduce((sum, opt) => sum + opt.votes, 0);
      return votesB - votesA;
    });
  }

  if (filtered.length === 0) {
    container.innerHTML = "<p class='text-center text-light'>Aucun sondage trouvé.</p>";
    return;
  }

  filtered.forEach((poll, index) => {
    let totalVotes = poll.options.reduce((sum, opt) => sum + opt.votes, 0) || 1;

    let col = document.createElement("div");
    col.className = "col-md-4";

    let card = document.createElement("div");
    card.className = "poll-card";

    // ID unique pour chaque graphique
    let chartId = "chart-" + index;

    card.innerHTML = `
      <div class="poll-question">${poll.question}</div>
      ${poll.options.map(opt => {
        let percentage = ((opt.votes / totalVotes) * 100).toFixed(1);
        return `
          <p class="mb-1">${opt.text} (${opt.votes} votes)</p>
          <div class="progress mb-3">
            <div class="progress-bar bg-info" style="width:${percentage}%">${percentage}%</div>
          </div>
        `;
      }).join("")}
      <canvas id="${chartId}" height="150"></canvas>
      <p class="text-muted"><i class="bi bi-calendar-x"></i> Sondage expiré</p>
    `;

    col.appendChild(card);
    container.appendChild(col);

    // 🎨 Création du camembert
    let ctx = document.getElementById(chartId).getContext("2d");
    new Chart(ctx, {
      type: "pie",
      data: {
        labels: poll.options.map(opt => opt.text),
        datasets: [{
          data: poll.options.map(opt => opt.votes),
          backgroundColor: ["#36A2EB", "#FF6384", "#FFCE56", "#4BC0C0", "#9966FF"]
        }]
      },
      options: {
        plugins: {
          legend: { labels: { color: "#fff" } }
        }
      }
    });
  });
}

document.getElementById("searchInput").addEventListener("input", renderPolls);
document.getElementById("sortSelect").addEventListener("change", renderPolls);

loadHistorique();
