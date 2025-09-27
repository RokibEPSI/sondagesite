function addOption() {
  const container = document.getElementById('options');
  const count = container.querySelectorAll('.option').length + 1;
  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'option';
  input.placeholder = `Option ${count}`;
  container.appendChild(input);
}

async function createPoll() {
  const question = document.getElementById('question').value.trim();
  const options = [...document.querySelectorAll('.option')]
      .map(o => o.value.trim()).filter(o => o !== '');
  
  if (!question || options.length < 2) {
    alert("Entrez une question et au moins deux options.");
    return;
  }

  await fetch('/api/polls', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ question, options })
  });

  location.reload();
}

async function loadPolls() {
  const res = await fetch('/api/polls');
  const polls = await res.json();
  const container = document.getElementById('polls');
  if (!container) return;

  container.innerHTML = '';

  polls.forEach((poll, pollIndex) => {
    const totalVotes = poll.options.reduce((s, o) => s + o.votes, 0);

    const col = document.createElement('div');
    col.className = 'col-md-6';

    const card = document.createElement('div');
    card.className = 'card shadow p-3';
    card.innerHTML = `<h4 class="mb-3">${poll.question}</h4>`;

    poll.options.forEach((o, i) => {
      const percent = totalVotes ? Math.round((o.votes / totalVotes) * 100) : 0;

      const optionDiv = document.createElement('div');
      optionDiv.className = 'mb-2';
      optionDiv.innerHTML = `
        <div class="d-flex justify-content-between">
          <button class="btn btn-sm btn-primary me-2">${o.text}</button>
          <span>${percent}%</span>
        </div>
        <div class="progress">
          <div class="progress-bar" style="width:${percent}%">${o.votes} votes</div>
        </div>
      `;

      optionDiv.querySelector('button').onclick = async () => {
        await fetch(`/api/vote/${pollIndex}/${i}`, { method: 'POST' });
        loadPolls();
      };

      card.appendChild(optionDiv);
    });

    // Ajout du graphique Chart.js
    const canvas = document.createElement('canvas');
    card.appendChild(canvas);

    col.appendChild(card);
    container.appendChild(col);

    // Crée le graphique circulaire
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
        plugins: {
          legend: { position: 'bottom' }
        }
      }
    });
  });
}

setInterval(loadPolls, 5000);
loadPolls();


function vote(pollId, optionIndex) {
  fetch(`/api/vote/${pollId}/${optionIndex}`, {
      method: "POST"
  })
  .then(res => {
      if (!res.ok) {
          return res.json().then(err => { throw err });
      }
      return res.json();
  })
  .then(data => {
      localStorage.setItem(`voted_${pollId}`, "true");
      loadPolls();
  })
  .catch(err => {
      alert(" " + (err.error || "Erreur inconnue"));
  });
}

loadPolls();
