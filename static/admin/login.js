async function loginAdmin(event) {
  event.preventDefault();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const errorEl = document.getElementById("login-error");

  errorEl.style.display = "none";
  errorEl.textContent = "";

  const response = await fetch("/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const message = await response.text();
    errorEl.textContent = message || "Login failed. Check your credentials.";
    errorEl.style.display = "block";
    return;
  }

  const data = await response.json();
  if (data.token) {
    localStorage.setItem("access_token", data.token);
    document.cookie = `access_token=${data.token}; path=/`;
  }
  if (data.refresh_token) {
    localStorage.setItem("refresh_token", data.refresh_token);
  }

  window.location.href = "/admin/dashboard";
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("admin-login-form");
  if (form) {
    form.addEventListener("submit", loginAdmin);
  }
});
