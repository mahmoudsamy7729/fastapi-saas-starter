function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(";").shift();
  }
  return null;
}

function getAccessToken() {
  return (
    localStorage.getItem("access_token") ||
    localStorage.getItem("token") ||
    getCookie("access_token")
  );
}

function getRefreshToken() {
  return localStorage.getItem("refresh_token");
}

function withAuthHeaders(headers) {
  const token = getAccessToken();
  if (token) {
    return { ...headers, Authorization: `Bearer ${token}` };
  }
  return headers;
}

async function refreshAccessToken() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return false;
  }

  const response = await fetch(`/refresh-token?token=${encodeURIComponent(refreshToken)}`, {
    method: "POST",
  });

  if (!response.ok) {
    return false;
  }

  const data = await response.json();
  if (data.token) {
    localStorage.setItem("access_token", data.token);
    document.cookie = `access_token=${data.token}; path=/`;
  }
  if (data.refresh_token) {
    localStorage.setItem("refresh_token", data.refresh_token);
  }
  return true;
}

async function apiFetch(url, options = {}) {
  const merged = {
    ...options,
    headers: withAuthHeaders(options.headers || {}),
  };
  let response = await fetch(url, merged);
  if (response.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      const retry = {
        ...options,
        headers: withAuthHeaders(options.headers || {}),
      };
      response = await fetch(url, retry);
    }
  }
  if (response.status === 401) {
    window.location.href = "/login";
    return null;
  }
  return response;
}

function adminLogout(event) {
  if (event) {
    event.preventDefault();
  }
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("token");
  document.cookie = "access_token=; Max-Age=0; path=/";
  window.location.href = "/login";
}

function formatDate(value) {
  if (!value) {
    return "--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

async function loadDashboardStats() {
  const response = await apiFetch("/dashboard/stats");
  if (!response || !response.ok) {
    return;
  }
  const data = await response.json();
  document.getElementById("stat-users").textContent = data.users ?? 0;
  document.getElementById("stat-subscriptions").textContent =
    data.subscriptions ?? 0;
  document.getElementById("stat-payments").textContent = data.payments ?? 0;
}

function setControlValue(id, value) {
  const el = document.getElementById(id);
  if (el && value !== null && value !== undefined) {
    el.value = value;
  }
}

function buildQueryFromForm(form) {
  const params = new URLSearchParams();
  const formData = new FormData(form);
  for (const [key, value] of formData.entries()) {
    if (value !== "") {
      params.set(key, value);
    }
  }
  params.set("offset", "0");
  return params;
}

async function loadUsersPage() {
  const form = document.getElementById("users-filter-form");
  const params = new URLSearchParams(window.location.search);

  setControlValue("limit", params.get("limit") || "10");
  setControlValue("is_active", params.get("is_active") || "");
  setControlValue("is_verified", params.get("is_verified") || "");
  setControlValue("is_admin", params.get("is_admin") || "");

  if (form) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const newParams = buildQueryFromForm(form);
      window.location.search = newParams.toString();
    });
  }

  const apiParams = new URLSearchParams();
  ["limit", "offset", "is_active", "is_verified", "is_admin"].forEach((key) => {
    const value = params.get(key);
    if (value !== null && value !== "") {
      apiParams.set(key, value);
    }
  });

  const response = await apiFetch(`/users?${apiParams.toString()}`);
  if (!response || !response.ok) {
    return;
  }

  const payload = await response.json();
  const tbody = document.getElementById("users-table");
  const count = document.getElementById("users-count");

  if (count) {
    count.textContent = `${payload.total ?? 0} total users`;
  }

  if (tbody) {
    tbody.innerHTML = "";
    if (!payload.data || payload.data.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="6" class="text-muted">No users found.</td></tr>';
    } else {
      payload.data.forEach((user) => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td><a href="/admin/users/${user.id}">${user.email}</a></td>
          <td>${user.username ?? "--"}</td>
          <td>${user.is_admin ? "Yes" : "No"}</td>
          <td>${user.is_active ? "Yes" : "No"}</td>
          <td>${user.is_verified ? "Yes" : "No"}</td>
          <td>${formatDate(user.created_at)}</td>
        `;
        tbody.appendChild(row);
      });
    }
  }

  const pagination = document.getElementById("users-pagination");
  if (pagination) {
    pagination.innerHTML = "";
    const baseParams = new URLSearchParams(params.toString());

    if (payload.prev_offset !== null && payload.prev_offset !== undefined) {
      baseParams.set("offset", payload.prev_offset);
      const prev = document.createElement("a");
      prev.className = "btn btn-outline-dark";
      prev.href = `/admin/users?${baseParams.toString()}`;
      prev.textContent = "Previous";
      pagination.appendChild(prev);
    }

    if (payload.next_offset !== null && payload.next_offset !== undefined) {
      baseParams.set("offset", payload.next_offset);
      const next = document.createElement("a");
      next.className = "btn btn-dark";
      next.href = `/admin/users?${baseParams.toString()}`;
      next.textContent = "Next";
      pagination.appendChild(next);
    }
  }
}

async function loadUserDetail() {
  const userId = document.body.dataset.userId;
  if (!userId) {
    return;
  }

  const response = await apiFetch(`/users/${userId}`);
  if (!response || !response.ok) {
    return;
  }
  const payload = await response.json();

  if (payload.user) {
    document.getElementById("detail-email").textContent = payload.user.email;
    document.getElementById("detail-username").textContent =
      payload.user.username ?? "--";
    document.getElementById("detail-admin").textContent = payload.user.is_admin
      ? "Yes"
      : "No";
    document.getElementById("detail-active").textContent = payload.user.is_active
      ? "Yes"
      : "No";
    document.getElementById("detail-verified").textContent =
      payload.user.is_verified ? "Yes" : "No";
    document.getElementById("detail-created").textContent = formatDate(
      payload.user.created_at
    );
  }

  document.getElementById("detail-subscriptions-count").textContent =
    payload.subscriptions_count ?? 0;
  document.getElementById("detail-transactions-count").textContent =
    payload.transactions_count ?? 0;

  const subResponse = await apiFetch(
    `/users/${userId}/subscriptions?limit=5&offset=0`
  );
  if (subResponse && subResponse.ok) {
    const subPayload = await subResponse.json();
    const container = document.getElementById("subscriptions-list");
    if (container) {
      if (!subPayload.data || subPayload.data.length === 0) {
        container.textContent = "No subscriptions found.";
      } else {
        container.innerHTML = subPayload.data
          .map(
            (sub) => `
            <div class="border-bottom py-2">
              <div class="fw-semibold">${sub.status}</div>
              <div class="text-muted small">
                ${sub.provider} - ${formatDate(sub.started_at)}
              </div>
            </div>
          `
          )
          .join("");
      }
    }
  }

  const txResponse = await apiFetch(
    `/users/${userId}/transactions?limit=5&offset=0`
  );
  if (txResponse && txResponse.ok) {
    const txPayload = await txResponse.json();
    const container = document.getElementById("transactions-list");
    if (container) {
      if (!txPayload.data || txPayload.data.length === 0) {
        container.textContent = "No transactions found.";
      } else {
        container.innerHTML = txPayload.data
          .map(
            (tx) => `
            <div class="border-bottom py-2">
              <div class="fw-semibold">${tx.status}</div>
              <div class="text-muted small">
                ${tx.provider} - ${tx.amount_cents / 100} ${tx.currency}
              </div>
            </div>
          `
          )
          .join("");
      }
    }
  }
}

async function loadUserSubscriptions() {
  const userId = document.body.dataset.userId;
  if (!userId) {
    return;
  }
  const params = new URLSearchParams(window.location.search);
  const apiParams = new URLSearchParams();
  const limit = params.get("limit") || "10";
  const offset = params.get("offset") || "0";
  apiParams.set("limit", limit);
  apiParams.set("offset", offset);

  const response = await apiFetch(
    `/users/${userId}/subscriptions?${apiParams.toString()}`
  );
  if (!response || !response.ok) {
    return;
  }

  const payload = await response.json();
  const tbody = document.getElementById("subscriptions-table");
  const count = document.getElementById("subscriptions-count");

  if (count) {
    count.textContent = `${payload.total ?? 0} total subscriptions`;
  }

  if (tbody) {
    tbody.innerHTML = "";
    if (!payload.data || payload.data.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="4" class="text-muted">No subscriptions found.</td></tr>';
    } else {
      payload.data.forEach((sub) => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${sub.status ?? "--"}</td>
          <td>${sub.provider ?? "--"}</td>
          <td>${formatDate(sub.started_at)}</td>
          <td>${formatDate(sub.current_period_end)}</td>
        `;
        tbody.appendChild(row);
      });
    }
  }

  const pagination = document.getElementById("subscriptions-pagination");
  if (pagination) {
    pagination.innerHTML = "";
    const baseParams = new URLSearchParams(params.toString());

    if (payload.prev_offset !== null && payload.prev_offset !== undefined) {
      baseParams.set("offset", payload.prev_offset);
      const prev = document.createElement("a");
      prev.className = "btn btn-outline-dark";
      prev.href = `/admin/users/${userId}/subscriptions?${baseParams.toString()}`;
      prev.textContent = "Previous";
      pagination.appendChild(prev);
    }

    if (payload.next_offset !== null && payload.next_offset !== undefined) {
      baseParams.set("offset", payload.next_offset);
      const next = document.createElement("a");
      next.className = "btn btn-dark";
      next.href = `/admin/users/${userId}/subscriptions?${baseParams.toString()}`;
      next.textContent = "Next";
      pagination.appendChild(next);
    }
  }
}

async function loadUserTransactions() {
  const userId = document.body.dataset.userId;
  if (!userId) {
    return;
  }
  const params = new URLSearchParams(window.location.search);
  const apiParams = new URLSearchParams();
  const limit = params.get("limit") || "10";
  const offset = params.get("offset") || "0";
  apiParams.set("limit", limit);
  apiParams.set("offset", offset);

  const response = await apiFetch(
    `/users/${userId}/transactions?${apiParams.toString()}`
  );
  if (!response || !response.ok) {
    return;
  }

  const payload = await response.json();
  const tbody = document.getElementById("transactions-table");
  const count = document.getElementById("transactions-count");

  if (count) {
    count.textContent = `${payload.total ?? 0} total transactions`;
  }

  if (tbody) {
    tbody.innerHTML = "";
    if (!payload.data || payload.data.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="4" class="text-muted">No transactions found.</td></tr>';
    } else {
      payload.data.forEach((tx) => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${tx.status ?? "--"}</td>
          <td>${tx.provider ?? "--"}</td>
          <td>${tx.amount_cents / 100} ${tx.currency}</td>
          <td>${formatDate(tx.created_at)}</td>
        `;
        tbody.appendChild(row);
      });
    }
  }

  const pagination = document.getElementById("transactions-pagination");
  if (pagination) {
    pagination.innerHTML = "";
    const baseParams = new URLSearchParams(params.toString());

    if (payload.prev_offset !== null && payload.prev_offset !== undefined) {
      baseParams.set("offset", payload.prev_offset);
      const prev = document.createElement("a");
      prev.className = "btn btn-outline-dark";
      prev.href = `/admin/users/${userId}/transactions?${baseParams.toString()}`;
      prev.textContent = "Previous";
      pagination.appendChild(prev);
    }

    if (payload.next_offset !== null && payload.next_offset !== undefined) {
      baseParams.set("offset", payload.next_offset);
      const next = document.createElement("a");
      next.className = "btn btn-dark";
      next.href = `/admin/users/${userId}/transactions?${baseParams.toString()}`;
      next.textContent = "Next";
      pagination.appendChild(next);
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const logoutLink = document.getElementById("admin-logout");
  if (logoutLink) {
    logoutLink.addEventListener("click", adminLogout);
  }

  const page = document.body.dataset.page;
  if (page === "dashboard") {
    loadDashboardStats();
  }
  if (page === "users") {
    loadUsersPage();
  }
  if (page === "user-detail") {
    loadUserDetail();
  }
  if (page === "user-subscriptions") {
    loadUserSubscriptions();
  }
  if (page === "user-transactions") {
    loadUserTransactions();
  }
});
