'use strict';

// ── State ──────────────────────────────────────────────────────────────────
const STORAGE_KEY = 'vibe_todos';

let todos = [];
let currentFilter = 'all';

// ── DOM refs ───────────────────────────────────────────────────────────────
const todoInput      = document.getElementById('todoInput');
const prioritySelect = document.getElementById('prioritySelect');
const addBtn         = document.getElementById('addBtn');
const todoList       = document.getElementById('todoList');
const emptyState     = document.getElementById('emptyState');
const statsText      = document.getElementById('statsText');
const clearCompleted = document.getElementById('clearCompleted');
const filterBtns     = document.querySelectorAll('.filter-btn');
const currentDateEl  = document.getElementById('currentDate');

// ── Init ───────────────────────────────────────────────────────────────────
function init() {
  todos = loadTodos();
  renderDate();
  render();

  addBtn.addEventListener('click', addTodo);
  todoInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') addTodo();
  });
  clearCompleted.addEventListener('click', clearCompletedTodos);
  filterBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      currentFilter = btn.dataset.filter;
      filterBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      render();
    });
  });
}

// ── Persistence ────────────────────────────────────────────────────────────
function loadTodos() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
  } catch {
    return [];
  }
}

function saveTodos() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
}

// ── CRUD ───────────────────────────────────────────────────────────────────
function addTodo() {
  const text = todoInput.value.trim();
  if (!text) {
    todoInput.focus();
    todoInput.classList.add('shake');
    setTimeout(() => todoInput.classList.remove('shake'), 400);
    return;
  }

  const todo = {
    id: Date.now(),
    text,
    priority: prioritySelect.value,
    completed: false,
    createdAt: new Date().toISOString(),
  };

  todos.unshift(todo);
  saveTodos();
  todoInput.value = '';
  prioritySelect.value = 'normal';
  render();
  todoInput.focus();
}

function toggleTodo(id) {
  const todo = todos.find((t) => t.id === id);
  if (todo) {
    todo.completed = !todo.completed;
    saveTodos();
    render();
  }
}

function deleteTodo(id) {
  todos = todos.filter((t) => t.id !== id);
  saveTodos();
  render();
}

function startEdit(id) {
  const item = document.querySelector(`[data-id="${id}"]`);
  if (!item) return;

  const todo = todos.find((t) => t.id === id);
  if (!todo) return;

  const textWrapper = item.querySelector('.todo-text-wrapper');
  const actions = item.querySelector('.todo-actions');

  // Replace text with input
  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'edit-input';
  input.value = todo.text;
  input.maxLength = 100;

  textWrapper.innerHTML = '';
  textWrapper.appendChild(input);
  actions.style.opacity = '1';
  input.focus();
  input.select();

  const finishEdit = () => {
    const newText = input.value.trim();
    if (newText && newText !== todo.text) {
      todo.text = newText;
      saveTodos();
    }
    render();
  };

  input.addEventListener('blur', finishEdit);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { input.blur(); }
    if (e.key === 'Escape') { input.value = todo.text; input.blur(); }
  });
}

function clearCompletedTodos() {
  todos = todos.filter((t) => !t.completed);
  saveTodos();
  render();
}

// ── Rendering ──────────────────────────────────────────────────────────────
function getFiltered() {
  switch (currentFilter) {
    case 'active':    return todos.filter((t) => !t.completed);
    case 'completed': return todos.filter((t) => t.completed);
    default:          return todos;
  }
}

function render() {
  const filtered = getFiltered();
  const total     = todos.length;
  const done      = todos.filter((t) => t.completed).length;
  const active    = total - done;

  // Stats
  statsText.textContent = `共 ${total} 项，${active} 项进行中，${done} 项已完成`;
  clearCompleted.style.display = done > 0 ? 'inline-block' : 'none';

  // Clear list (keep emptyState node)
  Array.from(todoList.children).forEach((child) => {
    if (child.id !== 'emptyState') child.remove();
  });

  if (filtered.length === 0) {
    emptyState.style.display = 'flex';
    return;
  }

  emptyState.style.display = 'none';

  filtered.forEach((todo) => {
    todoList.appendChild(createTodoItem(todo));
  });
}

function createTodoItem(todo) {
  const li = document.createElement('li');
  li.className = `todo-item priority-${todo.priority}${todo.completed ? ' completed' : ''}`;
  li.dataset.id = todo.id;

  // Checkbox
  const checkbox = document.createElement('div');
  checkbox.className = `todo-checkbox${todo.completed ? ' checked' : ''}`;
  checkbox.title = todo.completed ? '标记未完成' : '标记完成';
  checkbox.addEventListener('click', () => toggleTodo(todo.id));

  // Text wrapper
  const textWrapper = document.createElement('div');
  textWrapper.className = 'todo-text-wrapper';

  const textSpan = document.createElement('span');
  textSpan.className = 'todo-text';
  textSpan.textContent = todo.text;

  const metaDiv = document.createElement('div');
  metaDiv.className = 'todo-meta';

  const badge = document.createElement('span');
  badge.className = `priority-badge ${todo.priority}`;
  badge.textContent = priorityLabel(todo.priority);

  const timeSpan = document.createElement('span');
  timeSpan.className = 'todo-time';
  timeSpan.textContent = formatTime(todo.createdAt);

  metaDiv.appendChild(badge);
  metaDiv.appendChild(timeSpan);
  textWrapper.appendChild(textSpan);
  textWrapper.appendChild(metaDiv);

  // Actions
  const actions = document.createElement('div');
  actions.className = 'todo-actions';

  const editBtn = document.createElement('button');
  editBtn.className = 'action-btn edit-btn';
  editBtn.title = '编辑';
  editBtn.textContent = '✏️';
  editBtn.addEventListener('click', () => startEdit(todo.id));

  const deleteBtn = document.createElement('button');
  deleteBtn.className = 'action-btn delete-btn';
  deleteBtn.title = '删除';
  deleteBtn.textContent = '🗑️';
  deleteBtn.addEventListener('click', () => deleteTodo(todo.id));

  actions.appendChild(editBtn);
  actions.appendChild(deleteBtn);

  li.appendChild(checkbox);
  li.appendChild(textWrapper);
  li.appendChild(actions);

  return li;
}

// ── Helpers ────────────────────────────────────────────────────────────────
function priorityLabel(p) {
  return { normal: '普通', important: '重要', urgent: '紧急' }[p] || '普通';
}

function formatTime(iso) {
  const d = new Date(iso);
  const now = new Date();
  const diff = now - d;

  if (diff < 60000)        return '刚刚';
  if (diff < 3600000)      return `${Math.floor(diff / 60000)} 分钟前`;
  if (diff < 86400000)     return `${Math.floor(diff / 3600000)} 小时前`;
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
}

function renderDate() {
  const now = new Date();
  const options = { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' };
  currentDateEl.textContent = now.toLocaleDateString('zh-CN', options);
}

// ── Shake animation (CSS) ──────────────────────────────────────────────────
(function injectShakeStyle() {
  const style = document.createElement('style');
  style.textContent = `
    @keyframes shake {
      0%,100% { transform: translateX(0); }
      20%,60% { transform: translateX(-6px); }
      40%,80% { transform: translateX(6px); }
    }
    .shake { animation: shake 0.4s ease; border-color: #f44336 !important; }
  `;
  document.head.appendChild(style);
})();

// ── Start ──────────────────────────────────────────────────────────────────
init();
