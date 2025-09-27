async function loadPolls() {
  const res = await fetch('/api/polls');
  const polls = await res.json();
  const container = document.getElementById('polls');
  if (!container) return;

  container.innerHTML = '';

  polls.forEach((poll, pollIndex) => {
    const totalVotes = poll.options.reduce((s, o) => s + o.votes, 0);
    const hasVoted = localStorage.getItem(`voted_${pollIndex}`) === "true";

    const col = document.createElement('div');
    col.className = 'col-md-6';

   const card = document.createElement('div');
  card.className = 'card shadow p-3';

  // Titre + message si déjà voté
  card.innerHTML = `
    <h4 class="mb-3">${poll.question}</h4>
    ${hasVoted ? '<p class="text-success"><i class="bi bi-check-circle"></i> Vous avez déjà voté</p>' : ''}
  `;

    poll.options.forEach((o, i) => {
      const percent = totalVotes ? Math.round((o.votes / totalVotes) * 100) : 0;

      const optionDiv = document.createElement('div');
      optionDiv.className = 'mb-2';

      optionDiv.innerHTML = `
        <div class="d-flex justify-content-between">
          <button class="btn btn-sm btn-${hasVoted ? "secondary" : "primary"} me-2"
                  ${hasVoted ? "disabled" : ""}>
            ${o.text}
          </button>
          <span>${percent}%</span>
        </div>
        <div class="progress">
          <div class="progress-bar" style="width:${percent}%">${o.votes} votes</div>
        </div>
      `;

      // Si pas encore voté → autoriser le clic
      if (!hasVoted) {
        optionDiv.querySelector('button').onclick = async () => {
          await vote(pollIndex, i);
        };
      }

      card.appendChild(optionDiv);
    });

    // Graphique avec Chart.js
    const canvas = document.createElement('canvas');
    card.appendChild(canvas);

    col.appendChild(card);
    container.appendChild(col);

    const chartData = {
      labels: poll.options.map(o => o.text),
      datasets: [{
        data: poll.options.map(o => o.votes),
        backgroundColor: ['#4caf50', '#2196f3', '#ffc107', '#e91e63', '#9c27b0', '#ff5722']
      }]
    };

    new Chart(canvas, {
      type: 'pie',
      data: chartData,
      options: {
        plugins: { legend: { position: 'bottom' } }
      }
    });
  });
}

// Fonction de vote unifiée
async function vote(pollId, optionIndex) {
  try {
    const res = await fetch(`/api/vote/${pollId}/${optionIndex}`, { method: "POST" });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || "Erreur inconnue");
    }

    await res.json();
    localStorage.setItem(`voted_${pollId}`, "true");
    loadPolls();

  } catch (err) {
    alert(err.message);
  }
}

// Rafraîchir toutes les 5s
setInterval(loadPolls, 5000);
loadPolls();
