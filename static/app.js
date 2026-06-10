const state = {
  problems: [],
  currentProblem: null,
  submissions: [],
};

const nodes = {
  problemList: document.querySelector("#problemList"),
  problemIndex: document.querySelector("#problemIndex"),
  problemTitle: document.querySelector("#problemTitle"),
  difficulty: document.querySelector("#difficulty"),
  description: document.querySelector("#description"),
  inputDescription: document.querySelector("#inputDescription"),
  outputDescription: document.querySelector("#outputDescription"),
  examples: document.querySelector("#examples"),
  hints: document.querySelector("#hints"),
  codeEditor: document.querySelector("#codeEditor"),
  runBtn: document.querySelector("#runBtn"),
  submitBtn: document.querySelector("#submitBtn"),
  resetBtn: document.querySelector("#resetBtn"),
  refreshBtn: document.querySelector("#refreshBtn"),
  statusBadge: document.querySelector("#statusBadge"),
  resultStatus: document.querySelector("#resultStatus"),
  stdout: document.querySelector("#stdout"),
  stderr: document.querySelector("#stderr"),
  executeTime: document.querySelector("#executeTime"),
  submissionList: document.querySelector("#submissionList"),
};

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `HTTP ${response.status}`);
  }
  return response.json();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function statusText(status) {
  const map = {
    AC: "答案正确",
    WA: "答案错误",
    RE: "运行错误",
    TLE: "执行超时",
  };
  return map[status] || status || "未运行";
}

function renderProblemList() {
  nodes.problemList.innerHTML = state.problems
    .map((problem) => {
      const active = state.currentProblem?.id === problem.id ? " active" : "";
      return `
        <button class="problem-item${active}" type="button" data-id="${problem.id}">
          <span class="problem-number">${problem.id}</span>
          <span>
            <span class="problem-title">${escapeHtml(problem.title)}</span>
            <span class="problem-difficulty">${escapeHtml(problem.difficulty)}</span>
          </span>
          <span class="problem-dot" aria-hidden="true"></span>
        </button>
      `;
    })
    .join("");
}

function renderProblem(problem) {
  state.currentProblem = problem;
  renderProblemList();

  nodes.problemIndex.textContent = `${problem.id}.`;
  nodes.problemTitle.textContent = problem.title;
  nodes.difficulty.textContent = problem.difficulty;
  nodes.description.textContent = problem.description;
  nodes.inputDescription.textContent = problem.input_description;
  nodes.outputDescription.textContent = problem.output_description;
  nodes.codeEditor.value = problem.template;

  nodes.examples.innerHTML = problem.examples
    .map(
      (example, index) => `
        <article class="example-box">
          <strong>示例 ${index + 1}</strong>
          <pre>输入：${escapeHtml(example.input)}
输出：${escapeHtml(example.output)}</pre>
          <p>解释：${escapeHtml(example.explanation || "-")}</p>
        </article>
      `,
    )
    .join("");

  nodes.hints.innerHTML = problem.hints
    .map((hint) => `<li>${escapeHtml(hint)}</li>`)
    .join("");

  resetResult();
}

function setResult(result) {
  nodes.statusBadge.className = `status ${result.status || "idle"}`;
  nodes.statusBadge.textContent = result.status || "未运行";
  nodes.resultStatus.textContent = statusText(result.status);
  nodes.stdout.textContent = result.stdout?.trim() || "-";
  nodes.stderr.textContent = result.stderr?.trim() || "-";
  nodes.executeTime.textContent =
    typeof result.execute_time === "number" ? `${result.execute_time.toFixed(4)}s` : "-";
}

function resetResult() {
  nodes.statusBadge.className = "status idle";
  nodes.statusBadge.textContent = "未运行";
  nodes.resultStatus.textContent = "未运行";
  nodes.stdout.textContent = "-";
  nodes.stderr.textContent = "-";
  nodes.executeTime.textContent = "-";
}

function renderSubmissions() {
  if (state.submissions.length === 0) {
    nodes.submissionList.innerHTML = '<p class="empty">暂无提交记录</p>';
    return;
  }

  nodes.submissionList.innerHTML = state.submissions
    .map((item) => {
      const problem = state.problems.find((p) => p.id === item.problem_id);
      const title = problem ? problem.title : `题目 ${item.problem_id}`;
      const time = new Date(item.created_at).toLocaleString();
      return `
        <div class="submission-item">
          <span class="status ${item.status}">${item.status}</span>
          <span class="submission-meta">#${item.id} · ${escapeHtml(title)} · ${escapeHtml(time)}</span>
          <span class="submission-meta">${Number(item.execute_time || 0).toFixed(4)}s</span>
        </div>
      `;
    })
    .join("");
}

async function loadProblem(problemId) {
  const problem = await request(`/problems/${problemId}`);
  renderProblem(problem);
}

async function loadSubmissions() {
  state.submissions = await request("/submissions");
  renderSubmissions();
}

function setBusy(isBusy, actionText = "评测中") {
  nodes.runBtn.disabled = isBusy;
  nodes.submitBtn.disabled = isBusy;
  if (isBusy) {
    nodes.statusBadge.className = "status idle";
    nodes.statusBadge.textContent = actionText;
    nodes.resultStatus.textContent = actionText;
    nodes.stdout.textContent = "-";
    nodes.stderr.textContent = "-";
    nodes.executeTime.textContent = "-";
    return;
  }

  nodes.runBtn.innerHTML = '<span aria-hidden="true">▷</span>运行';
  nodes.submitBtn.innerHTML = '<span aria-hidden="true">↗</span>提交';
}

async function judgeCode(endpoint, options = {}) {
  if (!state.currentProblem) return;

  setBusy(true, options.label || "评测中");
  if (endpoint === "/run") {
    nodes.runBtn.innerHTML = '<span aria-hidden="true">▷</span>运行中';
  } else {
    nodes.submitBtn.innerHTML = '<span aria-hidden="true">↗</span>提交中';
  }

  try {
    const result = await request(endpoint, {
      method: "POST",
      body: JSON.stringify({
        problem_id: state.currentProblem.id,
        code: nodes.codeEditor.value,
      }),
    });
    setResult(result);
    if (options.refreshSubmissions) {
      await loadSubmissions();
    }
  } catch (error) {
    setResult({
      status: "RE",
      stdout: "",
      stderr: error.message,
      execute_time: 0,
    });
  } finally {
    setBusy(false);
  }
}

async function init() {
  state.problems = await request("/problems");
  renderProblemList();
  if (state.problems.length > 0) {
    await loadProblem(state.problems[0].id);
  }
  await loadSubmissions();
}

nodes.problemList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-id]");
  if (!button) return;
  loadProblem(Number(button.dataset.id));
});

nodes.runBtn.addEventListener("click", () => {
  judgeCode("/run", { label: "运行中" });
});
nodes.submitBtn.addEventListener("click", () => {
  judgeCode("/submit", { label: "提交中", refreshSubmissions: true });
});
nodes.refreshBtn.addEventListener("click", loadSubmissions);
nodes.resetBtn.addEventListener("click", () => {
  if (state.currentProblem) {
    nodes.codeEditor.value = state.currentProblem.template;
    resetResult();
  }
});

nodes.codeEditor.addEventListener("keydown", (event) => {
  if (event.key !== "Tab") return;
  event.preventDefault();
  const start = nodes.codeEditor.selectionStart;
  const end = nodes.codeEditor.selectionEnd;
  const value = nodes.codeEditor.value;
  nodes.codeEditor.value = `${value.slice(0, start)}    ${value.slice(end)}`;
  nodes.codeEditor.selectionStart = start + 4;
  nodes.codeEditor.selectionEnd = start + 4;
});

init().catch((error) => {
  nodes.problemList.innerHTML = `<p class="empty">${escapeHtml(error.message)}</p>`;
});
