const form = document.querySelector("#questionForm");
const input = document.querySelector("#questionInput");
const sendButton = document.querySelector("#sendButton");
const messages = document.querySelector("#messages");
const chunkCount = document.querySelector("#chunkCount");
const embeddingProvider = document.querySelector("#embeddingProvider");
const answerProvider = document.querySelector("#answerProvider");

function setStatus(status) {
  chunkCount.textContent = status.chunk_count ?? "-";
  embeddingProvider.textContent = status.embedding_provider ?? "-";
  answerProvider.textContent = status.answer_provider ?? "-";
}

function appendMessage(role, text, sources = []) {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  const content = document.createElement("span");
  content.textContent = text;
  article.appendChild(content);

  if (sources.length > 0) {
    const sourceList = document.createElement("div");
    sourceList.className = "sources";
    sources.forEach((item) => {
      const source = document.createElement("div");
      source.className = "source";
      const title = document.createElement("strong");
      title.textContent = `${item.source} / parca ${item.chunk_index} / skor ${item.score}`;
      const preview = document.createElement("span");
      preview.textContent = item.preview;
      source.append(title, preview);
      sourceList.appendChild(source);
    });
    article.appendChild(sourceList);
  }

  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
}

async function loadStatus() {
  const response = await fetch("/api/status");
  if (response.ok) {
    setStatus(await response.json());
  }
}

async function ask(question) {
  appendMessage("user", question);
  sendButton.disabled = true;
  sendButton.textContent = "Bekle";

  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const payload = await response.json();
    if (!response.ok) {
      appendMessage("assistant", payload.error || "Soru islenemedi.");
      return;
    }
    setStatus(payload.status || {});
    appendMessage("assistant", payload.answer, payload.sources || []);
  } catch (error) {
    appendMessage("assistant", `Sunucuya ulasilamadi: ${error}`);
  } finally {
    sendButton.disabled = false;
    sendButton.textContent = "Gonder";
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) return;
  input.value = "";
  ask(question);
});

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.question;
    input.focus();
  });
});

loadStatus();
