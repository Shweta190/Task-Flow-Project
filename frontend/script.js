const API_BASE = window.location.port === "8000"
    ? ""
    : (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
        ? "http://127.0.0.1:8000"
        : "");
const TOKEN_KEY = "taskflow_token";
const USER_KEY = "taskflow_user";
const TASKS_CACHE = "taskflow_tasks";

let authMode = "login";
let currentSort = "none";

document.addEventListener("DOMContentLoaded", () => {
    setupAuth();
    setupNav();
    setupTaskForm();
    setupQuickAdd();
    setupSearch();
    setupSort();
    setupClearAll();
    setupModal();
    setupLogout();

    if (getToken()) {
        showApp();
    } else {
        showAuth();
    }
});

// ─── Token helpers ───

function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(TASKS_CACHE);
}

function getAuthHeaders() {
    const token = getToken();
    return {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
}

function getStoredUser() {
    try {
        return JSON.parse(localStorage.getItem(USER_KEY) || "null");
    } catch {
        return null;
    }
}

function setStoredUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}

// ─── Auth ───

function setupAuth() {
    const tabLogin = document.getElementById("tab-login");
    const tabRegister = document.getElementById("tab-register");
    const form = document.getElementById("auth-form");
    const nameField = document.getElementById("name-field");
    const submitBtn = document.getElementById("auth-submit");

    tabLogin.addEventListener("click", () => {
        authMode = "login";
        tabLogin.classList.add("active");
        tabRegister.classList.remove("active");
        nameField.style.display = "none";
        submitBtn.textContent = "Login";
    });

    tabRegister.addEventListener("click", () => {
        authMode = "register";
        tabRegister.classList.add("active");
        tabLogin.classList.remove("active");
        nameField.style.display = "block";
        submitBtn.textContent = "Sign Up";
    });

    form.addEventListener("submit", handleAuthSubmit);
}

async function handleAuthSubmit(e) {
    e.preventDefault();
    const errorEl = document.getElementById("auth-error");
    errorEl.textContent = "";

    const email = document.getElementById("auth-email").value.trim();
    const password = document.getElementById("auth-password").value.trim();
    const name = document.getElementById("auth-name").value.trim();

    if (!email || !password) {
        errorEl.textContent = "Email and password are required.";
        return;
    }

    const endpoint = authMode === "login" ? "/auth/login" : "/auth/register";
    const body = authMode === "login"
        ? { email, password }
        : { email, password, name: name || null };

    try {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        const data = await res.json();

        if (res.ok) {
            setToken(data.access_token);
            setStoredUser(data.user);
            errorEl.textContent = "";
            showApp();
            return;
        } else {
            const msg = data.detail
                ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail))
                : "Authentication failed.";
            errorEl.textContent = msg;
        }
    } catch (err) {
        errorEl.textContent = "Cannot connect to server. Is the backend running?";
        console.error(err);
    }
}


function showAuth() {
    document.getElementById("auth-view").style.display = "flex";
    document.getElementById("app-view").style.display = "none";
}

function showApp() {
    document.getElementById("auth-view").style.display = "none";
    document.getElementById("app-view").style.display = "block";
    loadProfile();
    loadTasks();
}

// ─── Navigation ───

function setupNav() {
    document.querySelectorAll(".nav-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            const page = btn.dataset.page;
            document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            document.querySelectorAll(".page").forEach((p) => p.style.display = "none");
            document.getElementById(`page-${page}`).style.display = "block";
            if (page === "stats") loadStats();
            if (page === "profile") loadProfile();
        });
    });
}

// ─── Task Form ───

function setupTaskForm() {
    const form = document.getElementById("task-form");
    form.addEventListener("submit", handleTaskSubmit);
}

async function handleTaskSubmit(e) {
    e.preventDefault();

    const title = document.getElementById("title").value.trim();
    if (!title) {
        alert("Task title cannot be empty.");
        return;
    }

    const category = document.getElementById("category").value.trim() || "General";
    const priority = document.getElementById("priority").value;
    const dueDate = document.getElementById("due_date").value.trim() || null;

    try {
        const res = await fetch(`${API_BASE}/tasks`, {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({ title, category, priority, due_date: dueDate }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            alert(err.detail || "Failed to create task.");
            return;
        }

        document.getElementById("task-form").reset();
        document.getElementById("category").value = "General";
        document.getElementById("priority").value = "medium";
        loadTasks();
    } catch (err) {
        alert("Cannot connect to server.");
    }
}

// ─── Quick Add ───

function setupQuickAdd() {
    const form = document.getElementById("quick-add-form");
    form.addEventListener("submit", handleQuickAdd);
}

async function handleQuickAdd(e) {
    e.preventDefault();
    const desc = document.getElementById("quick-add-desc").value.trim();
    if (!desc) return;

    try {
        const res = await fetch(`${API_BASE}/tasks/quick-add`, {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({ description: desc }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            alert(err.detail || "Quick add failed.");
            return;
        }

        document.getElementById("quick-add-form").reset();
        loadTasks();
    } catch (err) {
        alert("Cannot connect to server.");
    }
}

// ─── Search ───

function setupSearch() {
    document.getElementById("search-btn").addEventListener("click", handleSearch);
    document.getElementById("search-input").addEventListener("keypress", (e) => {
        if (e.key === "Enter") handleSearch();
    });
}

async function handleSearch() {
    const title = document.getElementById("search-input").value.trim();
    const algo = document.getElementById("search-algo").value;
    const msgEl = document.getElementById("search-result-msg");

    if (!title) {
        msgEl.textContent = "Enter a title to search.";
        msgEl.className = "search-result-msg error";
        return;
    }

    try {
        const res = await fetch(
            `${API_BASE}/tasks/search?title=${encodeURIComponent(title)}&algo=${algo}`,
            { headers: getAuthHeaders() }
        );

        if (res.status === 404) {
            msgEl.textContent = `No task found with title "${title}".`;
            msgEl.className = "search-result-msg error";
            return;
        }

        if (!res.ok) {
            msgEl.textContent = "Search failed.";
            msgEl.className = "search-result-msg error";
            return;
        }

        const result = await res.json();
        msgEl.textContent = `Found: "${result.title}" (Task #${result.id})`;
        msgEl.className = "search-result-msg success";

        const items = document.querySelectorAll(".task-item");
        items.forEach((item) => {
            item.classList.remove("search-highlight");
            if (item.dataset.taskId === String(result.id)) {
                item.classList.add("search-highlight");
                item.scrollIntoView({ behavior: "smooth", block: "center" });
            }
        });
    } catch (err) {
        msgEl.textContent = "Cannot connect to server.";
        msgEl.className = "search-result-msg error";
    }
}

// ─── Sort ───

function setupSort() {
    document.getElementById("sort-select").addEventListener("change", (e) => {
        currentSort = e.target.value;
        loadTasks();
    });
}

// ─── Clear All ───

function setupClearAll() {
    document.getElementById("clear-all-btn").addEventListener("click", handleClearAll);
}

async function handleClearAll() {
    if (!confirm("Delete ALL tasks? This cannot be undone.")) return;

    try {
        const res = await fetch(`${API_BASE}/tasks/clear-all`, {
            method: "DELETE",
            headers: getAuthHeaders(),
        });

        if (!res.ok) {
            alert("Failed to clear tasks.");
            return;
        }

        loadTasks();
    } catch (err) {
        alert("Cannot connect to server.");
    }
}

// ─── Load Tasks ───

async function loadTasks() {
    const list = document.getElementById("task-list");
    list.textContent = "";

    const cached = localStorage.getItem(TASKS_CACHE);
    if (cached) {
        try {
            renderTasks(JSON.parse(cached));
        } catch {}
    }

    try {
        const url = currentSort && currentSort !== "none"
            ? `${API_BASE}/tasks?sort=${currentSort}`
            : `${API_BASE}/tasks`;
        const res = await fetch(url, { headers: getAuthHeaders() });

        if (res.status === 401) {
            clearToken();
            showAuth();
            return;
        }

        if (!res.ok) return;

        const tasks = await res.json();
        localStorage.setItem(TASKS_CACHE, JSON.stringify(tasks));
        renderTasks(tasks);
    } catch (err) {
        console.error("Fetch error:", err);
    }
}

function renderTasks(tasks) {
    const list = document.getElementById("task-list");
    list.textContent = "";

    if (!tasks || tasks.length === 0) {
        const empty = document.createElement("p");
        empty.textContent = "No tasks yet. Add one above.";
        empty.style.color = "#95a5a6";
        empty.style.padding = "12px";
        list.appendChild(empty);
        return;
    }

    tasks.forEach((task) => {
        list.appendChild(createTaskElement(task));
    });
}

function createTaskElement(task) {
    const item = document.createElement("div");
    item.className = `task-item priority-${task.priority || "medium"}`;
    if (task.status === "completed") item.classList.add("completed");
    item.dataset.taskId = task.id;

    const info = document.createElement("div");
    info.className = "task-info";

    const title = document.createElement("span");
    title.className = "task-title";
    title.textContent = task.title;
    info.appendChild(title);

    const meta = document.createElement("div");
    meta.className = "task-meta";

    const priorityBadge = document.createElement("span");
    priorityBadge.className = `badge badge-${task.priority || "medium"}`;
    priorityBadge.textContent = (task.priority || "medium").toUpperCase();
    meta.appendChild(priorityBadge);

    if (task.category) {
        const catBadge = document.createElement("span");
        catBadge.className = "badge badge-category";
        catBadge.textContent = task.category;
        meta.appendChild(catBadge);
    }

    if (task.due_date) {
        const dueText = document.createElement("span");
        dueText.textContent = `Due: ${task.due_date}`;
        meta.appendChild(dueText);
    }

    const statusBadge = document.createElement("span");
    statusBadge.className = `badge badge-status-${task.status === "completed" ? "done" : "pending"}`;
    statusBadge.textContent = task.status || "pending";
    meta.appendChild(statusBadge);

    info.appendChild(meta);
    item.appendChild(info);

    const actions = document.createElement("div");
    actions.className = "task-actions";

    const completeBtn = document.createElement("button");
    completeBtn.className = "btn-complete";
    completeBtn.textContent = task.status === "completed" ? "Undo" : "Done";
    completeBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        handleComplete(task.id);
    });
    actions.appendChild(completeBtn);

    const editBtn = document.createElement("button");
    editBtn.className = "btn-edit";
    editBtn.textContent = "Edit";
    editBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        handleEdit(task);
    });
    actions.appendChild(editBtn);

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "btn-delete";
    deleteBtn.textContent = "Delete";
    deleteBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        handleDelete(task.id);
    });
    actions.appendChild(deleteBtn);

    item.appendChild(actions);

    item.addEventListener("click", () => openTaskDetail(task));

    return item;
}

// ─── Task Actions ───

async function handleComplete(taskId) {
    try {
        const res = await fetch(`${API_BASE}/tasks/${taskId}/complete`, {
            method: "POST",
            headers: getAuthHeaders(),
        });

        if (!res.ok) {
            alert("Failed to update task.");
            return;
        }

        loadTasks();
    } catch (err) {
        alert("Cannot connect to server.");
    }
}

async function handleEdit(task) {
    const newTitle = prompt("Edit task title:", task.title);
    if (newTitle === null) return;
    const trimmed = newTitle.trim();
    if (!trimmed) {
        alert("Task title cannot be empty.");
        return;
    }

    const newCategory = prompt("Edit category:", task.category || "General");
    if (newCategory === null) return;

    const newPriority = prompt("Edit priority (low, medium, high):", task.priority || "medium");
    if (newPriority === null) return;

    const validPriorities = ["low", "medium", "high"];
    const priority = validPriorities.includes(newPriority.trim().toLowerCase())
        ? newPriority.trim().toLowerCase()
        : (task.priority || "medium");

    const newDueDate = prompt("Edit due date:", task.due_date || "");
    if (newDueDate === null) return;

    try {
        const res = await fetch(`${API_BASE}/tasks/${task.id}`, {
            method: "PUT",
            headers: getAuthHeaders(),
            body: JSON.stringify({
                title: trimmed,
                category: newCategory.trim() || "General",
                priority: priority,
                due_date: newDueDate.trim() || null,
            }),
        });

        if (!res.ok) {
            alert("Failed to update task.");
            return;
        }

        loadTasks();
    } catch (err) {
        alert("Cannot connect to server.");
    }
}

async function handleDelete(taskId) {
    if (!confirm("Delete this task?")) return;

    try {
        const res = await fetch(`${API_BASE}/tasks/${taskId}`, {
            method: "DELETE",
            headers: getAuthHeaders(),
        });

        if (!res.ok) {
            alert("Failed to delete task.");
            return;
        }

        loadTasks();
    } catch (err) {
        alert("Cannot connect to server.");
    }
}

// ─── Task Detail Modal ───

function setupModal() {
    document.getElementById("modal-close").addEventListener("click", closeModal);
    document.getElementById("modal-overlay").addEventListener("click", closeModal);
}

function openTaskDetail(task) {
    const modal = document.getElementById("task-detail-modal");
    const body = document.getElementById("task-detail-body");
    body.textContent = "";

    const fields = [
        { label: "Title", value: task.title },
        { label: "Category", value: task.category || "General" },
        { label: "Priority", value: (task.priority || "medium").toUpperCase() },
        { label: "Due Date", value: task.due_date || "Not set" },
        { label: "Status", value: task.status || "pending", isStatus: true },
        { label: "Task ID", value: String(task.id) },
    ];

    fields.forEach((f) => {
        const fieldDiv = document.createElement("div");
        fieldDiv.className = "detail-field";

        const label = document.createElement("div");
        label.className = "detail-label";
        label.textContent = f.label;
        fieldDiv.appendChild(label);

        const value = document.createElement("div");
        value.className = "detail-value";
        if (f.isStatus) {
            value.classList.add(f.value === "completed" ? "completed" : "pending");
        }
        value.textContent = f.value;
        fieldDiv.appendChild(value);

        body.appendChild(fieldDiv);
    });

    modal.style.display = "flex";
}

function closeModal() {
    document.getElementById("task-detail-modal").style.display = "none";
}

// ─── Statistics ───

async function loadStats() {
    try {
        const res = await fetch(`${API_BASE}/stats`, { headers: getAuthHeaders() });
        if (!res.ok) return;

        const stats = await res.json();

        document.getElementById("stat-total").textContent = stats.total;
        document.getElementById("stat-pending").textContent = stats.by_status.pending || 0;
        document.getElementById("stat-completed").textContent = stats.by_status.completed || 0;

        renderChart("chart-priority", stats.by_priority, "priority");
        renderChart("chart-category", stats.by_category, "category");
        renderChart("chart-status", stats.by_status, "status");
    } catch (err) {
        console.error("Stats error:", err);
    }
}

function renderChart(containerId, data, chartType) {
    const container = document.getElementById(containerId);
    container.textContent = "";

    const entries = Object.entries(data);
    if (entries.length === 0 || entries.every(([, v]) => v === 0)) {
        const empty = document.createElement("p");
        empty.textContent = "No data available.";
        empty.style.color = "#95a5a6";
        empty.style.padding = "8px";
        container.appendChild(empty);
        return;
    }

    const maxVal = Math.max(...entries.map(([, v]) => v), 1);

    entries.forEach(([label, count]) => {
        const row = document.createElement("div");
        row.className = "chart-row";

        const labelEl = document.createElement("div");
        labelEl.className = "chart-label";
        labelEl.textContent = label;
        row.appendChild(labelEl);

        const track = document.createElement("div");
        track.className = "chart-bar-track";

        const fill = document.createElement("div");
        fill.className = `chart-bar-fill bar-${chartType}`;
        fill.style.width = `${(count / maxVal) * 100}%`;
        track.appendChild(fill);

        row.appendChild(track);

        const countEl = document.createElement("div");
        countEl.className = "chart-count";
        countEl.textContent = String(count);
        row.appendChild(countEl);

        container.appendChild(row);
    });
}

// ─── Profile ───

async function loadProfile() {
    const user = getStoredUser();
    if (user) {
        renderProfile(user);
    }

    try {
        const res = await fetch(`${API_BASE}/auth/me`, { headers: getAuthHeaders() });
        if (res.status === 401) {
            clearToken();
            showAuth();
            return;
        }
        if (!res.ok) return;

        const freshUser = await res.json();
        setStoredUser(freshUser);
        renderProfile(freshUser);
    } catch (err) {
        console.error("Profile error:", err);
    }
}

function renderProfile(user) {
    const nameEl = document.getElementById("profile-name");
    const emailEl = document.getElementById("profile-email");
    const avatarEl = document.getElementById("profile-avatar");

    nameEl.textContent = user.name || "User";
    emailEl.textContent = user.email || "";
    avatarEl.textContent = (user.name || user.email || "U").charAt(0).toUpperCase();
}

// ─── Logout ───

function setupLogout() {
    document.getElementById("logout-btn").addEventListener("click", () => {
        clearToken();
        showAuth();
        document.getElementById("auth-form").reset();
    });
}
