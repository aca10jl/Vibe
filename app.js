const STORAGE_KEY = "vibe_todos";
const HISTORY_KEY = "vibe_history";

const state = {
  todos: loadData(STORAGE_KEY),
  history: loadData(HISTORY_KEY),
};

const form = document.getElementById("todo-form");
const todoList = document.getElementById("todo-list");
const historyList = document.getElementById("history-list");
const filterSelect = document.getElementById("status-filter");
const clearHistoryBtn = document.getElementById("clear-history");
const itemTemplate = document.getElementById("todo-item-template");

render();

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const formData = new FormData(form);

  const todo = {
    id: crypto.randomUUID(),
    title: String(formData.get("title")).trim(),
    description: String(formData.get("description") || "").trim(),
    priority: String(formData.get("priority")),
    dueDate: String(formData.get("dueDate")),
    completed: false,
    createdAt: new Date().toISOString(),
  };

  if (!todo.title) {
    return;
  }

  state.todos.unshift(todo);
  addHistory(`新增待办：${todo.title}`);
  form.reset();
  form.priority.value = "medium";
  persist();
  render();
});

filterSelect.addEventListener("change", () => {
  renderTodos();
});

clearHistoryBtn.addEventListener("click", () => {
  state.history = [];
  persist();
  renderHistory();
});

todoList.addEventListener("click", (event) => {
  const target = event.target;
  const item = target.closest(".todo-item");

  if (!item) {
    return;
  }

  const todoId = item.dataset.id;
  const todo = state.todos.find((entry) => entry.id === todoId);

  if (!todo) {
    return;
  }

  if (target.classList.contains("delete-btn")) {
    state.todos = state.todos.filter((entry) => entry.id !== todoId);
    addHistory(`删除待办：${todo.title}`);
    persist();
    render();
  }
});

todoList.addEventListener("change", (event) => {
  const target = event.target;
  if (!target.classList.contains("toggle-complete")) {
    return;
  }

  const item = target.closest(".todo-item");
  if (!item) {
    return;
  }

  const todoId = item.dataset.id;
  const todo = state.todos.find((entry) => entry.id === todoId);

  if (!todo) {
    return;
  }

  todo.completed = target.checked;
  const statusText = todo.completed ? "完成" : "恢复为进行中";
  addHistory(`${statusText}：${todo.title}`);
  persist();
  renderTodos();
});

function render() {
  renderTodos();
  renderHistory();
}

function renderTodos() {
  const filter = filterSelect.value;
  const todos = state.todos.filter((todo) => {
    if (filter === "all") {
      return true;
    }

    if (filter === "pending") {
      return !todo.completed;
    }

    return todo.completed;
  });

  todoList.innerHTML = "";

  if (!todos.length) {
    todoList.innerHTML = '<li class="empty">暂无待办，快添加一个吧！</li>';
    return;
  }

  for (const todo of todos) {
    const fragment = itemTemplate.content.cloneNode(true);
    const item = fragment.querySelector(".todo-item");
    const checkbox = fragment.querySelector(".toggle-complete");
    const title = fragment.querySelector(".title");
    const description = fragment.querySelector(".description");
    const priorityTag = fragment.querySelector(".priority-tag");
    const dueDate = fragment.querySelector(".due-date");

    item.dataset.id = todo.id;
    item.classList.toggle("completed", todo.completed);

    checkbox.checked = todo.completed;

    title.textContent = todo.title;
    description.textContent = todo.description || "无备注";

    priorityTag.textContent = `优先级：${priorityLabel(todo.priority)}`;
    priorityTag.classList.add(todo.priority);

    dueDate.textContent = `截止：${formatDate(todo.dueDate)}`;

    todoList.appendChild(fragment);
  }
}

function renderHistory() {
  historyList.innerHTML = "";

  if (!state.history.length) {
    historyList.innerHTML = '<li class="empty">暂无历史记录</li>';
    return;
  }

  for (const entry of state.history) {
    const li = document.createElement("li");
    li.innerHTML = `<span class="history-time">${formatDateTime(entry.time)}</span>${entry.message}`;
    historyList.appendChild(li);
  }
}

function priorityLabel(priority) {
  if (priority === "high") return "高";
  if (priority === "low") return "低";
  return "中";
}

function addHistory(message) {
  state.history.unshift({
    time: new Date().toISOString(),
    message,
  });

  state.history = state.history.slice(0, 100);
}

function persist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.todos));
  localStorage.setItem(HISTORY_KEY, JSON.stringify(state.history));
}

function loadData(key) {
  const raw = localStorage.getItem(key);
  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function formatDate(dateString) {
  if (!dateString) {
    return "未设置";
  }

  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) {
    return dateString;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

function formatDateTime(dateString) {
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) {
    return dateString;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}
