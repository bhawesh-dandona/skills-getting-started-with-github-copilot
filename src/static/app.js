document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("login-form");
  const loginContainer = document.getElementById("login-container");
  const authMessage = document.getElementById("auth-message");
  const accountStatus = document.getElementById("account-status");
  const logoutButton = document.getElementById("logout-button");
  const activitiesContainer = document.getElementById("activities-container");
  const signupContainer = document.getElementById("signup-container");
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  let accessToken = null;
  let currentUser = null;

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[character]);
  }

  function showAuthMessage(message, type = "error") {
    authMessage.textContent = message;
    authMessage.className = type;
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    if (!accessToken) {
      return;
    }

    try {
      const response = await fetch("/activities", {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!response.ok) {
        throw new Error("Unable to load activities.");
      }
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft = details.max_participants - details.participant_count;
        const participants = details.participants || [];
        const participantList = participants.length
          ? `<ul class="participants-list">${participants
              .map(
                (email) => `
                  <li class="participant-item">
                    <span class="participant-email">${escapeHtml(email)}</span>
                    ${currentUser.role === "admin" || email === currentUser.email
                      ? `<button
                          type="button"
                          class="participant-delete"
                          data-activity="${escapeHtml(name)}"
                          data-email="${escapeHtml(email)}"
                          aria-label="Remove ${escapeHtml(email)} from ${escapeHtml(name)}"
                          title="Remove participant"
                        >
                          ✕
                        </button>`
                      : ""}
                  </li>
                `
              )
              .join("")}</ul>`
          : '<p class="participants-empty">No participants yet.</p>';
        const registrationLabel = currentUser.role === "admin"
          ? "Participants:"
          : "Your registration:";

        activityCard.innerHTML = `
          <h4>${escapeHtml(name)}</h4>
          <p>${escapeHtml(details.description)}</p>
          <p><strong>Schedule:</strong> ${escapeHtml(details.schedule)}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants">
            <strong>${registrationLabel}</strong>
            ${participantList}
          </div> 
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });
    } catch (error) {
      activitiesList.innerHTML = "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  async function showMessage(message, type = "success") {
    messageDiv.textContent = message;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");

    setTimeout(() => {
      messageDiv.classList.add("hidden");
    }, 5000);
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${accessToken}` },
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        signupForm.reset();
        await fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  activitiesList.addEventListener("click", async (event) => {
    const deleteButton = event.target.closest(".participant-delete");
    if (!deleteButton) {
      return;
    }

    const activity = deleteButton.dataset.activity;
    const email = deleteButton.dataset.email;
    
    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/participants/${encodeURIComponent(email)}`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${accessToken}` },
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        await fetchActivities();
      } else {
        showMessage(result.detail || "Unable to remove participant.", "error");
      }
    } catch (error) {
      showMessage("Failed to remove participant.", "error");
      console.error("Error removing participant:", error);
    }
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const result = await response.json();
      if (!response.ok) {
        showAuthMessage(result.detail || "Sign in failed.");
        return;
      }

      accessToken = result.access_token;
      currentUser = result.user;
      loginForm.classList.add("hidden");
      loginContainer.querySelector("h3").textContent = "Account";
      accountStatus.textContent = `${currentUser.email} (${currentUser.role})`;
      accountStatus.classList.remove("hidden");
      logoutButton.classList.remove("hidden");
      activitiesContainer.classList.remove("hidden");
      signupContainer.classList.toggle("hidden", currentUser.role !== "student");
      authMessage.classList.add("hidden");
      await fetchActivities();
    } catch (error) {
      showAuthMessage("Unable to sign in. Please try again.");
      console.error("Error signing in:", error);
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      await fetch("/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}` },
      });
    } catch (error) {
      console.error("Error signing out:", error);
    }

    accessToken = null;
    currentUser = null;
    loginForm.reset();
    loginForm.classList.remove("hidden");
    loginContainer.querySelector("h3").textContent = "Sign In";
    accountStatus.classList.add("hidden");
    logoutButton.classList.add("hidden");
    activitiesContainer.classList.add("hidden");
    signupContainer.classList.add("hidden");
    activitiesList.innerHTML = "";
    messageDiv.classList.add("hidden");
  });
});
