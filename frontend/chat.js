const API_URL = "/api/v1/chat/message";
const MOOD_API_URL = "/api/v1/mood";
const CHALLENGE_REMINDERS_API_URL = "/api/v1/challenges/reminders";
const DASHBOARD_API_URL = "/api/v1/dashboard/overview";
const REMINDER_POLL_INTERVAL_MS = 120000;
const USER_ID = 1;

const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const chatWindow = document.getElementById("chatWindow");
const sendButton = document.getElementById("sendButton");
const statusPill = document.getElementById("statusPill");
const chatToggleBtn = document.getElementById("chatToggleBtn");
const chatWidget = document.getElementById("chatWidget");
const logActivityBtn = document.getElementById("logActivityBtn");
const logMoodBtn = document.getElementById("logMoodBtn");
const logMealBtn = document.getElementById("logMealBtn");
const dashboardStats = document.getElementById("dashboardStats");
const dashboardTodayLogs = document.getElementById("dashboardTodayLogs");
const dashboardWeeklySnapshot = document.getElementById("dashboardWeeklySnapshot");
const dashboardSuggestions = document.getElementById("dashboardSuggestions");
const dashboardStatus = document.getElementById("dashboardStatus");
const dashboardRefreshBtn = document.getElementById("dashboardRefreshBtn");

let isChatOpen = false;
let activityFlowState = null;
let moodFlowState = null;
let reminderPollTimer = null;
const shownReminderIds = new Set();

// Activity categories and their activities
const activityCategories = {
  wellbeing: {
    name: "Well Being",
    icon: "🧘",
    color: "wellbeing",
    activities: [
      { name: "Meditation", icon: "🧘", meta: "Mindfulness" },
      { name: "Yoga", icon: "🧘‍♀️", meta: "Flexibility & Balance" },
      { name: "Stretching", icon: "🤸", meta: "Recovery" },
      { name: "Breathing Exercise", icon: "💨", meta: "Relaxation" }
    ]
  },
  popular: {
    name: "Most Popular",
    icon: "⭐",
    color: "popular",
    activities: [
      { name: "Walking", icon: "🚶", meta: "Low Impact" },
      { name: "Running", icon: "🏃", meta: "Cardio" },
      { name: "Cycling", icon: "🚴", meta: "Endurance" },
      { name: "Swimming", icon: "🏊", meta: "Full Body" }
    ]
  },
  cardio: {
    name: "Cardio Vascular",
    icon: "❤️",
    color: "cardio",
    activities: [
      { name: "HIIT", icon: "⚡", meta: "High Intensity" },
      { name: "Jump Rope", icon: "🪢", meta: "Cardio Burst" },
      { name: "Rowing", icon: "🚣", meta: "Full Body Cardio" },
      { name: "Elliptical", icon: "🎯", meta: "Low Impact Cardio" }
    ]
  },
  sports: {
    name: "Sports",
    icon: "⚽",
    color: "sports",
    activities: [
      { name: "Badminton", icon: "🏸", meta: "Racket Sport" },
      { name: "Tennis", icon: "🎾", meta: "Racket Sport" },
      { name: "Basketball", icon: "🏀", meta: "Team Sport" },
      { name: "Football", icon: "⚽", meta: "Team Sport" }
    ]
  }
};

function formatDashboardTime(value) {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  
  const now = new Date();
  const diffMs = now - parsed;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  
  // Just now (less than 1 minute)
  if (diffMins < 1) {
    return "Just now";
  }
  
  // Minutes ago (1-59 minutes)
  if (diffMins < 60) {
    return `${diffMins} min ago`;
  }
  
  // Hours ago (1-23 hours)
  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }
  
  // Check if it's today
  const isToday = parsed.toDateString() === now.toDateString();
  
  if (isToday) {
    // Show time for today's older logs
    return parsed.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  }
  
  // Show date for other days
  if (diffDays < 7) {
    return parsed.toLocaleDateString("en-US", {
      weekday: "short"
    });
  }
  
  return parsed.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric"
  });
}

function renderTodayLogs(logs) {
  if (!logs || logs.length === 0) {
    dashboardTodayLogs.innerHTML = `<div class="dashboard-empty">Nothing has been logged today yet. Use the chat shortcuts to start filling your day board.</div>`;
    return;
  }

  const showAll = dashboardTodayLogs.dataset.showAll === "true";
  const displayLogs = showAll ? logs : logs.slice(0, 3);
  const hasMore = logs.length > 3;

  const logsHtml = displayLogs.map((entry) => `
    <article class="dashboard-log-item">
      <div class="dashboard-log-main">
        <span class="dashboard-log-icon">${getDashboardLogIcon(entry.item_type)}</span>
        <div>
          <div class="dashboard-log-title">${escapeHtml(entry.title)}</div>
          <div class="dashboard-log-detail">${escapeHtml(entry.detail)}</div>
        </div>
      </div>
      <div class="dashboard-log-time">${escapeHtml(formatDashboardTime(entry.created_at) || "Today")}</div>
    </article>
  `).join("");

  const showAllButton = hasMore && !showAll ? `
    <button class="dashboard-show-all-btn" onclick="toggleShowAllLogs()">
      Show All ${logs.length} Logs
    </button>
  ` : "";

  const showLessButton = showAll && hasMore ? `
    <button class="dashboard-show-all-btn" onclick="toggleShowAllLogs()">
      Show Less
    </button>
  ` : "";

  dashboardTodayLogs.innerHTML = logsHtml + showAllButton + showLessButton;
}

function toggleShowAllLogs() {
  const currentState = dashboardTodayLogs.dataset.showAll === "true";
  dashboardTodayLogs.dataset.showAll = !currentState;
  loadDashboard();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function getDashboardLogIcon(itemType) {
  const normalized = String(itemType || "").toLowerCase();
  if (normalized.includes("mood")) return "😊";
  if (normalized.includes("sleep")) return "😴";
  if (normalized.includes("water") || normalized.includes("hydration")) return "💧";
  if (normalized.includes("exercise") || normalized.includes("cardio")) return "💪";
  if (normalized.includes("sport")) return "⚽";
  if (normalized.includes("wellbeing") || normalized.includes("wellness")) return "🌟";
  if (normalized.includes("activity")) return "🏃";
  return "✓";
}

async function loadDashboard() {
  console.log("loadDashboard called");
  console.log("Dashboard elements:", {
    stats: !!dashboardStats,
    logs: !!dashboardTodayLogs,
    snapshot: !!dashboardWeeklySnapshot,
    suggestions: !!dashboardSuggestions
  });
  
  if (!dashboardStats || !dashboardTodayLogs || !dashboardWeeklySnapshot || !dashboardSuggestions) {
    console.warn("Dashboard elements not found, skipping load");
    return;
  }

  if (dashboardStatus) {
    dashboardStatus.textContent = "Loading live data...";
  }

  // Show loading skeleton
  dashboardStats.innerHTML = '<div class="dashboard-loading">Loading stats...</div>';
  dashboardTodayLogs.innerHTML = '<div class="dashboard-loading">Loading timeline...</div>';
  dashboardWeeklySnapshot.innerHTML = '<div class="dashboard-loading">Loading weekly data...</div>';
  dashboardSuggestions.innerHTML = '<div class="dashboard-loading">Loading suggestions...</div>';

  try {
    console.log("Fetching dashboard from:", `${DASHBOARD_API_URL}?user_id=${USER_ID}`);
    const response = await fetch(`${DASHBOARD_API_URL}?user_id=${USER_ID}`);
    if (!response.ok) {
      throw new Error(`Dashboard request failed: ${response.status}`);
    }

    const data = await response.json();
    console.log("Dashboard data received:", data);
    console.log("Today logs count:", data.today_logs?.length);
    renderDashboard(data);
    if (dashboardStatus) {
      dashboardStatus.textContent = "Updated just now";
    }
  } catch (error) {
    console.error("Could not load dashboard:", error);
    if (dashboardStatus) {
      dashboardStatus.textContent = "Could not load dashboard";
    }
    dashboardStats.innerHTML = `<div class="dashboard-empty">Dashboard data is unavailable right now.</div>`;
    dashboardTodayLogs.innerHTML = `<div class="dashboard-empty">No timeline available.</div>`;
    dashboardWeeklySnapshot.innerHTML = `<div class="dashboard-empty">Weekly snapshot unavailable.</div>`;
    dashboardSuggestions.innerHTML = `<div class="dashboard-empty">Suggestions are unavailable right now.</div>`;
  }
}

function refreshDashboardViews() {
  if (typeof loadDashboardData === "function") {
    loadDashboardData({ showLoading: false });
  }
  loadDashboard();
}

function renderDashboard(data) {
  console.log("renderDashboard called with data:", data);
  const stats = Array.isArray(data.daily_stats) ? data.daily_stats : [];
  const todayLogs = Array.isArray(data.today_logs) ? data.today_logs : [];
  const suggestions = Array.isArray(data.suggestions) ? data.suggestions : [];
  const weekly = data.weekly_snapshot || {};

  console.log("Rendering stats:", stats.length);
  console.log("Rendering today logs:", todayLogs.length, todayLogs);
  console.log("Rendering suggestions:", suggestions.length);

  dashboardStats.innerHTML = stats.map((stat) => `
    <article class="dashboard-stat dashboard-stat-${escapeHtml(stat.tone || "soft")}">
      <div class="dashboard-stat-label">${escapeHtml(stat.label)}</div>
      <div class="dashboard-stat-value">${escapeHtml(stat.value)}</div>
      <div class="dashboard-stat-detail">${escapeHtml(stat.detail || "")}</div>
    </article>
  `).join("");

  // Render today logs with show all functionality
  renderTodayLogs(todayLogs);

  console.log("Today logs HTML length:", dashboardTodayLogs.innerHTML.length);

  dashboardWeeklySnapshot.innerHTML = `
    <div class="dashboard-weekly-range">${escapeHtml(weekly.week_start || "")} to ${escapeHtml(weekly.week_end || "")}</div>
    <div class="dashboard-weekly-points">${escapeHtml(String(weekly.total_points ?? 0))} pts</div>
    <div class="dashboard-weekly-metrics">
      <div class="dashboard-weekly-metric">
        <span class="dashboard-weekly-metric-label">Mood logs</span>
        <span class="dashboard-weekly-metric-value">${escapeHtml(String(weekly.mood_logs ?? 0))}</span>
      </div>
      <div class="dashboard-weekly-metric">
        <span class="dashboard-weekly-metric-label">Activity sessions</span>
        <span class="dashboard-weekly-metric-value">${escapeHtml(String(weekly.activity_sessions ?? 0))}</span>
      </div>
      <div class="dashboard-weekly-metric">
        <span class="dashboard-weekly-metric-label">Exercise minutes</span>
        <span class="dashboard-weekly-metric-value">${escapeHtml(String(weekly.exercise_minutes ?? 0))}</span>
      </div>
      <div class="dashboard-weekly-metric">
        <span class="dashboard-weekly-metric-label">Completed challenges</span>
        <span class="dashboard-weekly-metric-value">${escapeHtml(String(weekly.completed_challenges ?? 0))}</span>
      </div>
    </div>
  `;

  dashboardSuggestions.innerHTML = suggestions.length ? suggestions.map((suggestion) => {
    // Check if this is a content suggestion with URL
    const hasUrl = suggestion.url && suggestion.url.trim() !== '';
    const contentTypeIcon = suggestion.content_type === 'video' ? '🎬' : 
                           suggestion.content_type === 'audio' ? '🎵' : 
                           suggestion.content_type === 'article' ? '📰' : '📄';
    
    return `
    <article class="dashboard-suggestion-card ${hasUrl ? 'has-url' : ''}">
      <div class="dashboard-suggestion-header">
        <div class="dashboard-suggestion-tag">${escapeHtml(suggestion.category_label)}</div>
        ${hasUrl ? `<span class="dashboard-content-type">${contentTypeIcon} ${escapeHtml(suggestion.content_type)}</span>` : ''}
      </div>
      <div class="dashboard-suggestion-title">${escapeHtml(suggestion.title)}</div>
      ${suggestion.duration ? `<div class="dashboard-suggestion-duration">${escapeHtml(suggestion.duration)}</div>` : ''}
      <div class="dashboard-suggestion-reason">${escapeHtml(suggestion.reason)}</div>
      ${hasUrl ? 
        `<a href="${escapeHtml(suggestion.url)}" target="_blank" rel="noopener noreferrer" class="dashboard-suggestion-btn dashboard-suggestion-link">
          Open Content →
        </a>` :
        `<button class="dashboard-suggestion-btn" data-dashboard-prompt="${escapeHtml(suggestion.action_prompt)}">Try In Chat</button>`
      }
    </article>
  `;
  }).join("") : `<div class="dashboard-empty">Keep logging through the week and I will surface focused suggestions here.</div>`;
}

function autoResizeTextarea() {
  messageInput.style.height = "auto";
  messageInput.style.height = `${Math.min(messageInput.scrollHeight, 120)}px`;
}

// ========== MOOD LOGGING FUNCTIONS ==========

const DEFAULT_MOOD_OPTIONS = [
  { label: "Ok", mood_label: "neutral", emoji: "😐", requires_reason: false },
  { label: "Not good", mood_label: "sad", emoji: "😕", requires_reason: true },
  { label: "Pretty Good", mood_label: "happy", emoji: "🙂", requires_reason: false },
  { label: "Awesome", mood_label: "great", emoji: "😄", requires_reason: false },
  { label: "Horrible", mood_label: "sad", emoji: "😣", requires_reason: true },
];

const DEFAULT_REASON_OPTIONS = [
  { label: "Work pressure", mood_label: "sad", emoji: "💼", requires_reason: false },
  { label: "Poor sleep", mood_label: "sad", emoji: "😴", requires_reason: false },
  { label: "Health issue", mood_label: "sad", emoji: "🤒", requires_reason: false },
  { label: "Family or relationship", mood_label: "sad", emoji: "👨‍👩‍👧‍👦", requires_reason: false },
  { label: "Food", mood_label: "sad", emoji: "🍽️", requires_reason: false },
  { label: "Travel", mood_label: "sad", emoji: "✈️", requires_reason: false },
  { label: "Friend", mood_label: "sad", emoji: "👥", requires_reason: false },
  { label: "Other", mood_label: "sad", emoji: "✍️", requires_reason: true },
];

function normalizeMoodOptions(options) {
  if (!Array.isArray(options) || options.length === 0) {
    return DEFAULT_MOOD_OPTIONS;
  }

  return options.map((option) => ({
    label: option.label || option.mood_label || "Mood",
    mood_label: option.mood_label || "neutral",
    emoji: option.emoji || "🙂",
    requires_reason: Boolean(option.requires_reason),
  }));
}

function normalizeReasonOptions(options) {
  if (!Array.isArray(options) || options.length === 0) {
    return DEFAULT_REASON_OPTIONS;
  }

  return options.map((option) => ({
    label: option.label || "Other",
    mood_label: option.mood_label || moodFlowState?.selectedMood?.mood_label || "sad",
    emoji: option.emoji || "✍️",
    requires_reason: Boolean(option.requires_reason),
  }));
}

async function fetchMoodOptions() {
  const response = await fetch(`${MOOD_API_URL}/quick-options`);
  if (!response.ok) {
    throw new Error("Failed to load mood options");
  }
  const data = await response.json();
  return normalizeMoodOptions(data.options);
}

function clearMoodFlowMessages() {
  document.querySelectorAll("[data-mood-flow='true']").forEach((element) => element.remove());
}

function createMessageElement(role, content, options = {}) {
  const message = document.createElement("div");
  const classes = ["message", role, options.messageClass].filter(Boolean);
  message.className = classes.join(" ");
  if (options.messageId) {
    message.id = options.messageId;
  }
  if (options.moodFlow) {
    message.dataset.moodFlow = "true";
  }

  const avatar = document.createElement("div");
  avatar.className = `avatar ${role === "assistant" ? "assistant-avatar" : ""}`.trim();
  avatar.textContent = role === "assistant" ? "A" : "Y";

  const stack = document.createElement("div");
  stack.className = "message-stack";

  const meta = document.createElement("div");
  meta.className = "message-meta";

  const name = document.createElement("p");
  name.className = "message-name";
  name.textContent = options.name || (role === "assistant" ? "FitCoach Assistant" : "You");

  meta.appendChild(name);

  const bubble = document.createElement("div");
  const bubbleClasses = ["bubble", role === "assistant" ? "assistant-bubble" : "user-bubble", options.bubbleClass].filter(Boolean);
  bubble.className = bubbleClasses.join(" ");

  if (options.bubbleId) {
    bubble.id = options.bubbleId;
  }

  if (typeof content === "string") {
    const paragraph = document.createElement("p");
    paragraph.textContent = content;
    bubble.appendChild(paragraph);
  } else if (content instanceof Node) {
    bubble.appendChild(content);
  }

  stack.append(meta, bubble);
  message.append(avatar, stack);
  return message;
}

function appendMessageElement(role, node, options = {}) {
  const message = createMessageElement(role, node, options);
  chatWindow.appendChild(message);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return message;
}

function createMoodButton(option, index, kind) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = kind === "reason" ? "mood-chip" : "mood-option-chip";
  button.dataset.moodIndex = String(index);

  const emoji = document.createElement("span");
  emoji.className = kind === "reason" ? "mood-chip-emoji" : "mood-option-emoji";
  emoji.textContent = option.emoji;

  const label = document.createElement("span");
  label.className = kind === "reason" ? "mood-chip-label" : "mood-option-label";
  label.textContent = option.label;

  button.append(emoji, label);
  return button;
}

function attachMoodSelectionListeners(container, moodOptions) {
  container.querySelectorAll("[data-mood-index]").forEach((button) => {
    button.addEventListener("click", async () => {
      const index = parseInt(button.dataset.moodIndex, 10);
      await handleMoodSelection(moodOptions[index], button);
    });
  });
}

function renderMoodSelectionMessage(moodOptions) {
  const content = document.createElement("div");
  content.className = "mood-flow-content";
  content.id = "moodSelectionMessage";

  const promptRow = document.createElement("div");
  promptRow.className = "mood-flow-prompt-row";

  const promptText = document.createElement("div");
  promptText.className = "mood-flow-prompt-text";
  promptText.innerHTML = "<span class='mood-flow-prompt-icon'>😊</span><span>How are you feeling today?</span>";

  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "mood-flow-cancel-link";
  cancelBtn.textContent = "Cancel";
  cancelBtn.addEventListener("click", cancelMoodFlow);

  promptRow.append(promptText, cancelBtn);

  const helper = document.createElement("p");
  helper.className = "mood-flow-helper";
  helper.textContent = "Pick the closest mood and I will log it with you.";

  const chipRow = document.createElement("div");
  chipRow.className = "mood-chip-row";
  chipRow.id = "moodChoiceRow";

  moodOptions.forEach((option, index) => {
    chipRow.appendChild(createMoodButton(option, index, "mood"));
  });

  attachMoodSelectionListeners(chipRow, moodOptions);

  content.append(promptRow, helper, chipRow);
  appendMessageElement("assistant", content, {
    moodFlow: true,
    messageClass: "mood-flow-inline",
    bubbleClass: "mood-flow-bubble",
    messageId: "moodSelectionWrapper",
  });
}

function renderReasonSelectionMessage(flowData, reasonOptions) {
  const content = document.createElement("div");
  content.className = "mood-flow-content";
  content.id = "moodReasonMessage";

  const promptRow = document.createElement("div");
  promptRow.className = "mood-flow-prompt-row";

  const promptText = document.createElement("div");
  promptText.className = "mood-flow-prompt-text";
  promptText.innerHTML = "<span class='mood-flow-prompt-icon'>💬</span><span>" + (flowData.prompt || "What is the reason?") + "</span>";

  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "mood-flow-cancel-link";
  cancelBtn.textContent = "Cancel";
  cancelBtn.addEventListener("click", cancelMoodFlow);

  promptRow.append(promptText, cancelBtn);

  const helper = document.createElement("p");
  helper.className = "mood-flow-helper";
  helper.textContent = "Choose one that fits best or add your own reason.";

  const chipRow = document.createElement("div");
  chipRow.className = "mood-chip-row mood-chip-row-reason";
  chipRow.id = "moodReasonRow";

  reasonOptions.forEach((option, index) => {
    chipRow.appendChild(createMoodButton(option, index, "reason"));
  });

  chipRow.querySelectorAll("[data-mood-index]").forEach((button) => {
    button.addEventListener("click", () => {
      const index = parseInt(button.dataset.moodIndex, 10);
      handleReasonSelection(reasonOptions[index], button);
    });
  });

  content.append(promptRow, helper, chipRow);
  appendMessageElement("assistant", content, {
    moodFlow: true,
    messageClass: "mood-flow-inline",
    bubbleClass: "mood-flow-bubble",
    messageId: "moodReasonWrapper",
  });
}

function renderOtherReasonInput() {
  const existing = document.getElementById("moodOtherReasonWrapper");
  if (existing) {
    existing.remove();
  }

  const content = document.createElement("div");
  content.className = "mood-flow-content";
  content.id = "moodOtherReasonMessage";

  const prompt = document.createElement("p");
  prompt.className = "mood-flow-helper mood-flow-helper-left";
  prompt.textContent = "Tell me a little more so I can understand it better.";

  const textarea = document.createElement("textarea");
  textarea.className = "mood-reason-textarea";
  textarea.id = "otherReasonText";
  textarea.placeholder = "Type your reason here...";

  const submitBtn = document.createElement("button");
  submitBtn.type = "button";
  submitBtn.className = "mood-reason-submit";
  submitBtn.id = "otherReasonSubmit";
  submitBtn.textContent = "Add reason";

  submitBtn.addEventListener("click", async () => {
    const customReason = textarea.value.trim();
    if (!customReason) {
      return;
    }
    appendMessage("user", customReason);
    await submitMoodReason(customReason, "Other");
  });

  textarea.addEventListener("keydown", async (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      const customReason = textarea.value.trim();
      if (customReason) {
        appendMessage("user", customReason);
        await submitMoodReason(customReason, "Other");
      }
    }
  });

  content.append(prompt, textarea, submitBtn);
  const wrapper = appendMessageElement("assistant", content, {
    moodFlow: true,
    messageClass: "mood-flow-inline",
    bubbleClass: "mood-flow-bubble",
    messageId: "moodOtherReasonWrapper",
  });

  setTimeout(() => textarea.focus(), 0);
  return wrapper;
}

async function showMoodSelection() {
  clearMoodFlowMessages();

  moodFlowState = {
    step: "select",
    draftId: null,
    moodOptions: [...DEFAULT_MOOD_OPTIONS],
    reasonOptions: [...DEFAULT_REASON_OPTIONS],
    selectedMood: null,
  };

  renderMoodSelectionMessage(DEFAULT_MOOD_OPTIONS);

  try {
    const moodOptions = await fetchMoodOptions();
    if (!moodFlowState || moodFlowState.step !== "select") {
      return;
    }
    moodFlowState.moodOptions = moodOptions;

    const selectionWrapper = document.getElementById("moodSelectionWrapper");
    if (selectionWrapper) {
      const chipRow = selectionWrapper.querySelector("#moodChoiceRow");
      if (chipRow) {
        chipRow.replaceChildren();
        moodOptions.forEach((option, index) => {
          chipRow.appendChild(createMoodButton(option, index, "mood"));
        });
        attachMoodSelectionListeners(chipRow, moodOptions);
      }
    }
  } catch (error) {
    console.warn("Using fallback mood options:", error);
  }
}

async function handleMoodSelection(moodOption, btnElement) {
  if (!moodFlowState) return;

  const selectionWrapper = document.getElementById("moodSelectionWrapper");
  const chipRow = selectionWrapper?.querySelector("#moodChoiceRow");
  if (chipRow) {
    chipRow.querySelectorAll("[data-mood-index]").forEach((button) => button.classList.remove("selected"));
  }

  btnElement.classList.add("selected");
  moodFlowState.selectedMood = moodOption;
  moodFlowState.step = "draft";

  appendMessage("user", `${moodOption.emoji} ${moodOption.label}`);

  try {
    const response = await fetch(`${MOOD_API_URL}/draft/start`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: USER_ID,
        mood_label: moodOption.mood_label,
        raw_text: moodOption.label,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to start mood flow");
    }

    const data = await response.json();
    moodFlowState.draftId = data.draft_id;
    moodFlowState.reasonOptions = normalizeReasonOptions(data.reason_options);

    if (data.status === "pending") {
      showReasonSelection(data);
      return;
    }

    if (data.status === "completed") {
      showMoodConfirmation(data);
      moodFlowState = null;
    }
  } catch (error) {
    console.error("Error starting mood flow:", error);
    appendMessage("assistant", "Sorry, I could not start mood logging right now. Please try again.");
    moodFlowState = null;
    clearMoodFlowMessages();
  }
}

function showReasonSelection(flowData) {
  if (!moodFlowState) return;

  const reasonOptions = normalizeReasonOptions(flowData.reason_options || moodFlowState.reasonOptions);
  moodFlowState.step = "reason";
  moodFlowState.draftId = flowData.draft_id || moodFlowState.draftId;
  moodFlowState.reasonOptions = reasonOptions;

  const selectionWrapper = document.getElementById("moodSelectionWrapper");
  if (selectionWrapper) {
    const helper = selectionWrapper.querySelector(".mood-flow-helper");
    if (helper) {
      helper.textContent = "That is okay. Pick the reason that feels closest.";
    }
  }

  const existing = document.getElementById("moodReasonWrapper");
  if (existing) {
    existing.remove();
  }

  renderReasonSelectionMessage(flowData, reasonOptions);
}

function handleReasonSelection(reasonOption, chipElement) {
  if (!moodFlowState) return;

  const reasonWrapper = document.getElementById("moodReasonWrapper");
  const reasonRow = reasonWrapper?.querySelector("#moodReasonRow");
  if (reasonRow) {
    reasonRow.querySelectorAll("[data-mood-index]").forEach((button) => button.classList.remove("selected"));
  }
  chipElement.classList.add("selected");

  if (reasonOption.requires_reason) {
    renderOtherReasonInput();
    return;
  }

  appendMessage("user", reasonOption.label);
  submitMoodReason(reasonOption.label, reasonOption.label);
}

async function submitMoodReason(reason, reasonLabel) {
  if (!moodFlowState?.draftId || !moodFlowState.selectedMood) {
    return;
  }

  const otherReasonWrapper = document.getElementById("moodOtherReasonWrapper");
  if (otherReasonWrapper) {
    otherReasonWrapper.remove();
  }

  try {
    const response = await fetch(`${MOOD_API_URL}/draft/${moodFlowState.draftId}?user_id=${USER_ID}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        reason: reason,
        reason_label: reasonLabel,
        raw_text: reason,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to update mood draft");
    }

    const data = await response.json();

    if (data.status === "completed") {
      showMoodConfirmation(data);
      moodFlowState = null;
    } else if (data.status === "pending") {
      showReasonSelection(data);
    }
  } catch (error) {
    console.error("Error saving mood reason:", error);
    appendMessage("assistant", "Sorry, I could not save that reason right now. Please try again.");
  }
}

function showMoodConfirmation(data) {
  const emoji = data.emoji || data.draft?.emoji || "🙂";
  const moodLabel = (data.mood_label || data.draft?.mood_label || "mood").toString();
  const displayLabel = moodLabel.charAt(0).toUpperCase() + moodLabel.slice(1);
  const messageText = data.prompt || data.log_result?.message || `${displayLabel} mood recorded.`;

  appendMessage("assistant", `${emoji} ${messageText}`);
  refreshDashboardViews();
}

async function cancelMoodFlow() {
  const draftId = moodFlowState?.draftId;

  try {
    if (draftId) {
      await fetch(`${MOOD_API_URL}/draft/${draftId}?user_id=${USER_ID}`, {
        method: "DELETE",
      });
    }
  } catch (error) {
    console.warn("Could not cancel mood draft on backend:", error);
  } finally {
    moodFlowState = null;
    clearMoodFlowMessages();
    appendMessage("assistant", "Mood logging cancelled. Let me know if you'd like to try again!");
  }
}

// ========== END MOOD LOGGING FUNCTIONS ==========

// ========== MEAL LOGGING FUNCTIONS ==========

const MEAL_API_URL = "/api/v1/meals";

let mealFlowState = null;

const MEAL_TYPES = [
  { key: "breakfast", label: "Breakfast", emoji: "🍳" },
  { key: "lunch", label: "Lunch", emoji: "🍱" },
  { key: "dinner", label: "Dinner", emoji: "🍽️" },
  { key: "snack", label: "Snack", emoji: "🍪" },
];

// Quick-select food items (frequently logged foods)
const QUICK_FOOD_ITEMS = [
  { name: "Organic Kosher Hamburger Dill Chips", defaultServing: 1, unit: "serving", emoji: "🥒" },
  { name: "Chicken Hot Dogs", defaultServing: 1, unit: "piece", emoji: "🌭" },
  { name: "Coffee Ice Cream", defaultServing: 1, unit: "scoop", emoji: "🍨" },
  { name: "Chicken Sandwich Sauce", defaultServing: 2, unit: "tablespoon", emoji: "🥫" },
  { name: "Kosher Hamburger Dill Chips", defaultServing: 1, unit: "serving", emoji: "🥒" },
  { name: "Ice Cream Sandwiches", defaultServing: 1, unit: "piece", emoji: "🍦" },
  { name: "Chicken Sausage Sweet Potato Crust Pizza", defaultServing: 2, unit: "slice", emoji: "🍕" },
  { name: "Pizza Dough", defaultServing: 1, unit: "serving", emoji: "🍕" },
  { name: "Honey and Sriracha Chicken", defaultServing: 1, unit: "serving", emoji: "🍗" },
];

// Serving units by food category
const SERVING_UNITS = {
  "drink": ["cup", "glass", "bottle", "ml"],
  "solid": ["serving", "piece", "slice", "bowl"],
  "rice": ["cup", "bowl", "serving"],
  "sauce": ["tablespoon", "teaspoon", "serving"],
  "snack": ["serving", "piece", "handful", "bag"],
};

function clearMealFlowMessages() {
  document.querySelectorAll("[data-meal-flow='true']").forEach((el) => el.remove());
}

function showMealLogging() {
  clearMealFlowMessages();
  
  mealFlowState = {
    step: "meal_type",
    mealType: null,
    mealName: null,
    estimate: null,
  };
  
  renderMealTypeSelection();
}

function renderMealTypeSelection() {
  const content = document.createElement("div");
  content.className = "meal-flow-content";
  
  const prompt = document.createElement("p");
  prompt.className = "meal-flow-prompt";
  prompt.textContent = "What type of meal would you like to log?";
  
  const chipRow = document.createElement("div");
  chipRow.className = "meal-flow-chip-row";
  chipRow.id = "mealTypeRow";
  
  MEAL_TYPES.forEach((mealType, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "meal-flow-chip";
    button.dataset.mealIndex = index;
    button.innerHTML = `<span class="meal-chip-emoji">${mealType.emoji}</span> <span>${mealType.label}</span>`;
    chipRow.appendChild(button);
  });
  
  content.append(prompt, chipRow);
  
  const wrapper = appendMessageElement("assistant", content, {
    mealFlow: true,
    messageClass: "meal-flow-inline",
    bubbleClass: "meal-flow-bubble",
    messageId: "mealTypeWrapper",
  });
  
  wrapper.dataset.mealFlow = "true";
  
  chipRow.querySelectorAll("[data-meal-index]").forEach((button) => {
    button.addEventListener("click", async () => {
      const index = parseInt(button.dataset.mealIndex, 10);
      await handleMealTypeSelection(MEAL_TYPES[index], button);
    });
  });
}

async function handleMealTypeSelection(mealType, btnElement) {
  if (!mealFlowState) return;
  
  const chipRow = document.getElementById("mealTypeRow");
  if (chipRow) {
    chipRow.querySelectorAll("[data-meal-index]").forEach((button) => 
      button.classList.remove("selected")
    );
  }
  
  btnElement.classList.add("selected");
  mealFlowState.mealType = mealType.key;
  mealFlowState.step = "meal_name";
  
  appendMessage("user", `${mealType.emoji} ${mealType.label}`);
  
  renderMealNameInput(mealType);
}

function renderMealNameInput(mealType) {
  const content = document.createElement("div");
  content.className = "meal-flow-content";
  
  const prompt = document.createElement("p");
  prompt.className = "meal-flow-prompt";
  prompt.textContent = `What did you have for ${mealType.label.toLowerCase()}?`;
  
  // Quick select chips
  const quickSelectLabel = document.createElement("p");
  quickSelectLabel.className = "meal-flow-helper";
  quickSelectLabel.textContent = "Quick select:";
  
  const quickChipsRow = document.createElement("div");
  quickChipsRow.className = "meal-quick-chips-row";
  
  QUICK_FOOD_ITEMS.forEach((food, index) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "meal-quick-chip";
    chip.dataset.foodIndex = index;
    chip.innerHTML = `<span class="meal-chip-emoji">${food.emoji}</span> <span>${food.name}</span>`;
    quickChipsRow.appendChild(chip);
  });
  
  // Or manual input
  const orDivider = document.createElement("p");
  orDivider.className = "meal-flow-divider";
  orDivider.textContent = "Or type your own:";
  
  const inputWrapper = document.createElement("div");
  inputWrapper.className = "meal-flow-input-wrapper";
  
  const input = document.createElement("input");
  input.type = "text";
  input.id = "mealNameInput";
  input.className = "meal-flow-input";
  input.placeholder = "e.g., Chicken burger, Pizza, Dal and rice";
  input.autocomplete = "off";
  
  const submitBtn = document.createElement("button");
  submitBtn.type = "button";
  submitBtn.className = "meal-flow-submit-btn";
  submitBtn.textContent = "Next";
  
  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "meal-flow-cancel-link";
  cancelBtn.textContent = "Cancel";
  cancelBtn.addEventListener("click", cancelMealFlow);
  
  inputWrapper.append(input, submitBtn);
  content.append(prompt, quickSelectLabel, quickChipsRow, orDivider, inputWrapper, cancelBtn);
  
  const wrapper = appendMessageElement("assistant", content, {
    mealFlow: true,
    messageClass: "meal-flow-inline",
    bubbleClass: "meal-flow-bubble",
    messageId: "mealNameWrapper",
  });
  
  wrapper.dataset.mealFlow = "true";
  
  // Quick chip selection
  quickChipsRow.querySelectorAll("[data-food-index]").forEach((chip) => {
    chip.addEventListener("click", async () => {
      const index = parseInt(chip.dataset.foodIndex, 10);
      const food = QUICK_FOOD_ITEMS[index];
      
      quickChipsRow.querySelectorAll(".meal-quick-chip").forEach((c) => 
        c.classList.remove("selected")
      );
      chip.classList.add("selected");
      
      // Store selected food and go to serving size selection
      await handleQuickFoodSelection(food);
    });
  });
  
  // Manual input submission
  const handleSubmit = async () => {
    const mealName = input.value.trim();
    if (!mealName) {
      input.style.borderColor = "#e74c3c";
      return;
    }
    
    submitBtn.disabled = true;
    submitBtn.textContent = "Estimating...";
    
    // For manual entry, ask for serving size before estimating
    await handleManualFoodEntry(mealName);
  };
  
  submitBtn.addEventListener("click", handleSubmit);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  });
  
  setTimeout(() => input.focus(), 0);
}

async function handleMealNameSubmit(mealName) {
  if (!mealFlowState) return;
  
  mealFlowState.mealName = mealName;
  mealFlowState.step = "estimating";
  
  appendMessage("user", mealName);
  
  try {
    const response = await fetch(`${MEAL_API_URL}/estimate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        meal_name: mealName,
        servings: 1.0,
        meal_type: mealFlowState.mealType,
      }),
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error("API Error:", response.status, errorText);
      throw new Error(`Failed to estimate nutrition: ${response.status}`);
    }
    
    const estimate = await response.json();
    console.log("Nutrition estimate received:", estimate);
    mealFlowState.estimate = estimate;
    mealFlowState.step = "confirm";
    
    renderMealConfirmation(estimate);
  } catch (error) {
    console.error("Error estimating meal:", error);
    appendMessage("assistant", "Sorry, I couldn't estimate the nutrition. Please try again.");
    mealFlowState = null;
    clearMealFlowMessages();
  }
}

async function handleQuickFoodSelection(food) {
  if (!mealFlowState) return;
  
  mealFlowState.mealName = food.name;
  mealFlowState.selectedFood = food;
  mealFlowState.step = "serving_size";
  
  appendMessage("user", `${food.emoji} ${food.name}`);
  
  renderServingSizeSelection(food);
}

async function handleManualFoodEntry(mealName) {
  if (!mealFlowState) return;
  
  mealFlowState.mealName = mealName;
  mealFlowState.selectedFood = {
    name: mealName,
    defaultServing: 1,
    unit: "serving",
    emoji: "🍽️"
  };
  mealFlowState.step = "serving_size";
  
  appendMessage("user", mealName);
  
  renderServingSizeSelection(mealFlowState.selectedFood);
}

function renderServingSizeSelection(food) {
  const content = document.createElement("div");
  content.className = "meal-flow-content";
  
  const prompt = document.createElement("p");
  prompt.className = "meal-flow-prompt";
  prompt.textContent = "How much did you have?";
  
  const servingWrapper = document.createElement("div");
  servingWrapper.className = "meal-serving-wrapper";
  
  // Quantity input
  const quantityGroup = document.createElement("div");
  quantityGroup.className = "meal-serving-group";
  
  const quantityLabel = document.createElement("label");
  quantityLabel.className = "meal-serving-label";
  quantityLabel.textContent = "Quantity:";
  quantityLabel.htmlFor = "servingQuantity";
  
  const quantityInput = document.createElement("input");
  quantityInput.type = "number";
  quantityInput.id = "servingQuantity";
  quantityInput.className = "meal-serving-input";
  quantityInput.value = food.defaultServing || 1;
  quantityInput.min = "0.1";
  quantityInput.step = "0.5";
  
  quantityGroup.append(quantityLabel, quantityInput);
  
  // Unit selection
  const unitGroup = document.createElement("div");
  unitGroup.className = "meal-serving-group";
  
  const unitLabel = document.createElement("label");
  unitLabel.className = "meal-serving-label";
  unitLabel.textContent = "Unit:";
  unitLabel.htmlFor = "servingUnit";
  
  const unitSelect = document.createElement("select");
  unitSelect.id = "servingUnit";
  unitSelect.className = "meal-serving-select";
  
  // Determine appropriate units based on food name
  const units = getAppropriateUnits(food.name);
  units.forEach((unit) => {
    const option = document.createElement("option");
    option.value = unit;
    option.textContent = unit;
    if (unit === food.unit) {
      option.selected = true;
    }
    unitSelect.appendChild(option);
  });
  
  unitGroup.append(unitLabel, unitSelect);
  
  servingWrapper.append(quantityGroup, unitGroup);
  
  // Submit button
  const submitBtn = document.createElement("button");
  submitBtn.type = "button";
  submitBtn.className = "meal-flow-confirm-btn";
  submitBtn.textContent = "Estimate Nutrition";
  
  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "meal-flow-cancel-link";
  cancelBtn.textContent = "Cancel";
  cancelBtn.addEventListener("click", cancelMealFlow);
  
  content.append(prompt, servingWrapper, submitBtn, cancelBtn);
  
  const wrapper = appendMessageElement("assistant", content, {
    mealFlow: true,
    messageClass: "meal-flow-inline",
    bubbleClass: "meal-flow-bubble",
    messageId: "servingSizeWrapper",
  });
  
  wrapper.dataset.mealFlow = "true";
  
  submitBtn.addEventListener("click", async () => {
    const quantity = parseFloat(quantityInput.value);
    const unit = unitSelect.value;
    
    if (!quantity || quantity <= 0) {
      quantityInput.style.borderColor = "#e74c3c";
      return;
    }
    
    submitBtn.disabled = true;
    submitBtn.textContent = "Estimating...";
    
    appendMessage("user", `${quantity} ${unit}${quantity > 1 ? 's' : ''}`);
    
    await handleServingSizeSubmit(quantity, unit);
  });
  
  setTimeout(() => quantityInput.focus(), 0);
}

function getAppropriateUnits(foodName) {
  const nameLower = foodName.toLowerCase();
  
  // Drinks
  if (nameLower.includes("coffee") || nameLower.includes("tea") || 
      nameLower.includes("juice") || nameLower.includes("milk") || 
      nameLower.includes("water") || nameLower.includes("soda")) {
    return ["cup", "glass", "bottle", "ml"];
  }
  
  // Rice, pasta, grains
  if (nameLower.includes("rice") || nameLower.includes("pasta") || 
      nameLower.includes("noodle") || nameLower.includes("biryani")) {
    return ["cup", "bowl", "serving", "plate"];
  }
  
  // Sauces and condiments
  if (nameLower.includes("sauce") || nameLower.includes("dressing") || 
      nameLower.includes("dip") || nameLower.includes("mayo")) {
    return ["tablespoon", "teaspoon", "serving"];
  }
  
  // Pizza and sliced items
  if (nameLower.includes("pizza") || nameLower.includes("pie")) {
    return ["slice", "piece", "whole"];
  }
  
  // Ice cream and desserts
  if (nameLower.includes("ice cream") || nameLower.includes("dessert")) {
    return ["scoop", "cup", "serving", "piece"];
  }
  
  // Hot dogs, sandwiches, burgers
  if (nameLower.includes("hot dog") || nameLower.includes("sandwich") || 
      nameLower.includes("burger") || nameLower.includes("wrap")) {
    return ["piece", "whole", "half"];
  }
  
  // Chips and snacks
  if (nameLower.includes("chip") || nameLower.includes("snack") || 
      nameLower.includes("cracker")) {
    return ["serving", "bag", "handful", "oz"];
  }
  
  // Default
  return ["serving", "piece", "cup", "bowl"];
}

async function handleServingSizeSubmit(quantity, unit) {
  if (!mealFlowState) return;
  
  mealFlowState.servings = quantity;
  mealFlowState.servingUnit = unit;
  mealFlowState.step = "estimating";
  
  try {
    const response = await fetch(`${MEAL_API_URL}/estimate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        meal_name: mealFlowState.mealName,
        servings: quantity,
        meal_type: mealFlowState.mealType,
      }),
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error("API Error:", response.status, errorText);
      throw new Error(`Failed to estimate nutrition: ${response.status}`);
    }
    
    const estimate = await response.json();
    console.log("Nutrition estimate received:", estimate);
    mealFlowState.estimate = estimate;
    mealFlowState.step = "confirm";
    
    renderMealConfirmation(estimate);
  } catch (error) {
    console.error("Error estimating meal:", error);
    appendMessage("assistant", "Sorry, I couldn't estimate the nutrition. Please try again.");
    mealFlowState = null;
    clearMealFlowMessages();
  }
}

function renderMealConfirmation(estimate) {
  const content = document.createElement("div");
  content.className = "meal-flow-content";
  
  // Create conversational text message
  const messageText = document.createElement("p");
  messageText.className = "meal-estimate-text";
  messageText.innerHTML = `I estimate <strong>${estimate.calories} calories</strong> for your ${estimate.meal_name || 'meal'}. <span class="meal-macros-inline">Protein: ${estimate.protein_grams}g • Carbs: ${estimate.carbs_grams}g • Fat: ${estimate.fat_grams}g</span>`;
  
  // Action buttons inline
  const buttonRow = document.createElement("div");
  buttonRow.className = "meal-action-buttons";
  
  const confirmBtn = document.createElement("button");
  confirmBtn.type = "button";
  confirmBtn.className = "meal-action-btn meal-action-primary";
  confirmBtn.textContent = "Log meal";
  
  const editBtn = document.createElement("button");
  editBtn.type = "button";
  editBtn.className = "meal-action-btn meal-action-secondary";
  editBtn.textContent = "Edit values";
  
  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "meal-action-btn meal-action-cancel";
  cancelBtn.textContent = "Cancel";
  cancelBtn.addEventListener("click", cancelMealFlow);
  
  buttonRow.append(confirmBtn, editBtn, cancelBtn);
  content.append(messageText, buttonRow);
  
  const wrapper = appendMessageElement("assistant", content, {
    mealFlow: true,
    messageClass: "meal-flow-inline",
    bubbleClass: "meal-flow-bubble",
    messageId: "mealConfirmWrapper",
  });
  
  wrapper.dataset.mealFlow = "true";
  
  confirmBtn.addEventListener("click", () => handleMealConfirm(estimate));
  editBtn.addEventListener("click", () => renderMealEdit(estimate));
}

function renderMealEdit(estimate) {
  const content = document.createElement("div");
  content.className = "meal-flow-content";
  
  const prompt = document.createElement("p");
  prompt.className = "meal-flow-prompt";
  prompt.textContent = "Edit nutrition values:";
  
  const form = document.createElement("div");
  form.className = "meal-edit-form";
  form.innerHTML = `
    <div class="meal-edit-field">
      <label for="editCalories">Calories</label>
      <input type="number" id="editCalories" value="${estimate.calories}" min="0" step="1">
    </div>
    <div class="meal-edit-field">
      <label for="editProtein">Protein (g)</label>
      <input type="number" id="editProtein" value="${estimate.protein_grams}" min="0" step="1">
    </div>
    <div class="meal-edit-field">
      <label for="editCarbs">Carbs (g)</label>
      <input type="number" id="editCarbs" value="${estimate.carbs_grams}" min="0" step="1">
    </div>
    <div class="meal-edit-field">
      <label for="editFat">Fat (g)</label>
      <input type="number" id="editFat" value="${estimate.fat_grams}" min="0" step="1">
    </div>
  `;
  
  const buttonRow = document.createElement("div");
  buttonRow.className = "meal-flow-button-row";
  
  const saveBtn = document.createElement("button");
  saveBtn.type = "button";
  saveBtn.className = "meal-flow-confirm-btn";
  saveBtn.textContent = "✓ Save & Log";
  
  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "meal-flow-cancel-link";
  cancelBtn.textContent = "Cancel";
  cancelBtn.addEventListener("click", cancelMealFlow);
  
  buttonRow.append(saveBtn);
  content.append(prompt, form, buttonRow, cancelBtn);
  
  const wrapper = appendMessageElement("assistant", content, {
    mealFlow: true,
    messageClass: "meal-flow-inline",
    bubbleClass: "meal-flow-bubble",
    messageId: "mealEditWrapper",
  });
  
  wrapper.dataset.mealFlow = "true";
  
  saveBtn.addEventListener("click", () => {
    const editedEstimate = {
      calories: parseInt(document.getElementById("editCalories").value) || estimate.calories,
      protein_grams: parseInt(document.getElementById("editProtein").value) || estimate.protein_grams,
      carbs_grams: parseInt(document.getElementById("editCarbs").value) || estimate.carbs_grams,
      fat_grams: parseInt(document.getElementById("editFat").value) || estimate.fat_grams,
      confidence: estimate.confidence,
      notes: "Values edited by user",
    };
    handleMealConfirm(editedEstimate);
  });
  
  setTimeout(() => document.getElementById("editCalories")?.focus(), 0);
}

async function handleMealConfirm(estimate) {
  if (!mealFlowState) return;
  
  mealFlowState.step = "logging";
  
  try {
    const response = await fetch(`${MEAL_API_URL}/log`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: USER_ID,
        meal_type: mealFlowState.mealType,
        meal_name: mealFlowState.mealName,
        calories: estimate.calories,
        protein_grams: estimate.protein_grams,
        carbs_grams: estimate.carbs_grams,
        fat_grams: estimate.fat_grams,
        notes: estimate.notes,
      }),
    });
    
    if (!response.ok) {
      throw new Error("Failed to log meal");
    }
    
    const result = await response.json();
    
    clearMealFlowMessages();
    
    appendMessage("assistant", 
      `✅ Logged ${mealFlowState.mealName} - ${estimate.calories} calories added to your daily total!`
    );
    
    // Refresh dashboard to show updated calorie balance
    refreshDashboardViews();
    
    mealFlowState = null;
  } catch (error) {
    console.error("Error logging meal:", error);
    appendMessage("assistant", "Sorry, I couldn't log your meal. Please try again.");
    mealFlowState = null;
    clearMealFlowMessages();
  }
}

function cancelMealFlow() {
  mealFlowState = null;
  clearMealFlowMessages();
  appendMessage("assistant", "Meal logging cancelled. Let me know if you'd like to try again!");
}

// ========== END MEAL LOGGING FUNCTIONS ==========

// ========== CONVERSATION STARTERS ==========

const CONVERSATION_STARTERS = [
  { text: "How am I doing this week?", icon: "📊", category: "progress" },
  { text: "I'm feeling stressed", icon: "😰", category: "mood" },
  { text: "What should I do today?", icon: "💡", category: "suggestion" },
  { text: "Give me a weekly review", icon: "📈", category: "progress" },
  { text: "I want to exercise more", icon: "💪", category: "goal" },
  
];

function showConversationStarters() {
  // Only show if there are no user messages yet (system messages are ok)
  const userMessages = chatWindow.querySelectorAll(".message.user");
  if (userMessages.length > 0) {
    return; // Don't show if user has already sent messages
  }
  
  // Also don't show if starters already exist
  const existingStarters = document.getElementById("conversationStartersWrapper");
  if (existingStarters) {
    return;
  }

  const content = document.createElement("div");
  content.className = "conversation-starters-content";
  content.id = "conversationStartersMessage";

  const header = document.createElement("div");
  header.className = "conversation-starters-header";
  header.innerHTML = `
    <span class="conversation-starters-icon">💬</span>
    <span class="conversation-starters-title">Try asking me...</span>
  `;

  const helper = document.createElement("p");
  helper.className = "conversation-starters-helper";
  helper.textContent = "I can help you track progress, understand patterns, and stay motivated.";

  const grid = document.createElement("div");
  grid.className = "conversation-starters-grid";

  CONVERSATION_STARTERS.forEach((starter) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `conversation-starter-chip conversation-starter-${starter.category}`;
    button.innerHTML = `
      <span class="conversation-starter-icon">${starter.icon}</span>
      <span class="conversation-starter-text">${starter.text}</span>
    `;
    button.addEventListener("click", (e) => {
      e.stopPropagation(); // Prevent click from bubbling up
      // Remove starters
      const wrapper = document.getElementById("conversationStartersWrapper");
      if (wrapper) {
        wrapper.remove();
      }
      // Send the message
      sendMessage(starter.text);
    });
    grid.appendChild(button);
  });

  content.append(header, helper, grid);
  
  const wrapper = appendMessageElement("assistant", content, {
    messageClass: "conversation-starters-inline",
    bubbleClass: "conversation-starters-bubble",
    messageId: "conversationStartersWrapper",
  });
  
  wrapper.dataset.conversationStarters = "true";
}

// ========== END CONVERSATION STARTERS ==========

function toggleChat() {
  isChatOpen = !isChatOpen;
  chatToggleBtn.classList.toggle("active", isChatOpen);
  chatWidget.classList.toggle("active", isChatOpen);
  
  if (isChatOpen) {
    setTimeout(() => messageInput.focus(), 300);
    startReminderPolling();
    // Fetch reminders immediately when chat opens
    setTimeout(() => fetchAndRenderReminders(), 500);
    clearNotificationBadge(); // Clear badge when opening chat
    showConversationStarters(); // Show conversation starters when chat opens
  } else {
    stopReminderPolling();
  }
}

function handleShortcutClick(shortcutText) {
  // Send the shortcut text as a user message
  sendMessage(shortcutText);
}

function showActivityCategories() {
  const card = document.createElement("div");
  card.className = "activity-flow-card";
  card.innerHTML = `
    <div class="activity-flow-header">
      <div class="activity-flow-title">
        <span class="icon">🏃</span>
        Choose Activity Category
      </div>
      <button class="activity-cancel-btn" onclick="cancelActivityFlow()">Cancel</button>
    </div>
    <div class="category-grid">
      ${Object.entries(activityCategories).map(([key, cat]) => `
        <div class="category-card category-${cat.color}" onclick="selectCategory('${key}')">
          <div class="category-icon">${cat.icon}</div>
          <div class="category-name">${cat.name}</div>
        </div>
      `).join('')}
    </div>
  `;
  chatWindow.appendChild(card);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  
  activityFlowState = { step: 'category' };
}

function selectCategory(categoryKey) {
  const category = activityCategories[categoryKey];
  activityFlowState = { step: 'activity', category: categoryKey };
  
  const card = document.createElement("div");
  card.className = "activity-flow-card";
  card.innerHTML = `
    <div class="activity-flow-header">
      <div class="activity-flow-title">
        <span class="icon">${category.icon}</span>
        ${category.name}
      </div>
      <button class="activity-cancel-btn" onclick="cancelActivityFlow()">Cancel</button>
    </div>
    <div class="breadcrumb">
      <span class="breadcrumb-item" onclick="showActivityCategories()">Categories</span>
      <span class="breadcrumb-separator">›</span>
      <span class="breadcrumb-item active">${category.name}</span>
    </div>
    <div class="activity-list">
      ${category.activities.map(act => `
        <div class="activity-item" onclick='selectActivity(${JSON.stringify(act).replace(/'/g, "&apos;")})'>
          <div class="activity-item-icon">${act.icon}</div>
          <div class="activity-item-info">
            <div class="activity-item-name">${act.name}</div>
            <div class="activity-item-meta">${act.meta}</div>
          </div>
        </div>
      `).join('')}
    </div>
  `;
  chatWindow.appendChild(card);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function selectActivity(activity) {
  activityFlowState = { 
    ...activityFlowState, 
    step: 'details', 
    activity: activity.name,
    activityIcon: activity.icon
  };
  
  const today = new Date().toISOString().split('T')[0];
  
  const card = document.createElement("div");
  card.className = "activity-flow-card";
  card.innerHTML = `
    <div class="activity-flow-header">
      <div class="activity-flow-title">
        <span class="icon">${activity.icon}</span>
        Log ${activity.name}
      </div>
      <button class="activity-cancel-btn" onclick="cancelActivityFlow()">Cancel</button>
    </div>
    <div class="input-group">
      <label class="input-label">Date</label>
      <input type="date" class="input-field" id="activityDate" value="${today}" max="${today}">
    </div>
    <div class="input-row">
      <div class="input-group">
        <label class="input-label">Duration (minutes)</label>
        <input type="number" class="input-field" id="activityDuration" placeholder="30" min="1">
      </div>
      <div class="input-group">
        <label class="input-label">Time</label>
        <input type="time" class="input-field time-input-native" id="activityTime" required>
      </div>
    </div>
    <div class="action-buttons">
      <button class="btn-secondary-action" onclick="cancelActivityFlow()">Cancel</button>
      <button class="btn-primary-action" onclick="submitActivity()">Log Activity</button>
    </div>
  `;
  chatWindow.appendChild(card);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  
  // Native time input - no initialization needed
  // Set current time as default
  setTimeout(() => {
    const timeInput = document.getElementById('activityTime');
    if (timeInput && !timeInput.value) {
      const now = new Date();
      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');
      timeInput.value = `${hours}:${minutes}`;
    }
  }, 100);
}
async function submitActivity() {
  const date = document.getElementById('activityDate')?.value;
  const duration = document.getElementById('activityDuration')?.value;
  const time = document.getElementById('activityTime')?.value;
  
  if (!duration) {
    alert('Please enter duration');
    return;
  }

  const activityName = activityFlowState?.activity;
  const normalizedName = String(activityName || '').trim().toLowerCase();
  const supportedNames = new Set(['walking', 'running', 'yoga', 'badminton', 'basketball', 'football']);
  const datePart = date ? ` on ${date}` : '';
  const timePart = time ? ` at ${time}` : '';
  const logText = supportedNames.has(normalizedName)
    ? `I did ${normalizedName} for ${duration} minutes${datePart}${timePart}.`
    : `I did exercise for ${duration} minutes${datePart}${timePart}. It was ${activityName}.`;
  activityFlowState = null;
  await sendMessage(logText);
  return;
  
  const category = activityCategories[activityFlowState.category];
  
  const card = document.createElement("div");
  card.className = "success-card";
  card.innerHTML = `
    <div class="success-header">
      <span class="success-icon">✅</span>
      <span class="success-title">Activity Logged!</span>
    </div>
    <div class="success-details">
      <div class="success-row">
        <span class="success-label">Activity</span>
        <span class="success-value">${activityFlowState.activityIcon} ${activityFlowState.activity}</span>
      </div>
      <div class="success-row">
        <span class="success-label">Category</span>
        <span class="success-value">${category.name}</span>
      </div>
      <div class="success-row">
        <span class="success-label">Duration</span>
        <span class="success-value">${duration} minutes</span>
      </div>
      <div class="success-row">
        <span class="success-label">Date</span>
        <span class="success-value">${date || 'Today'}</span>
      </div>
      ${time ? `<div class="success-row">
        <span class="success-label">Time</span>
        <span class="success-value">${time}</span>
      </div>` : ''}
    </div>
  `;
  chatWindow.appendChild(card);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  
  activityFlowState = null;
}

function cancelActivityFlow() {
  activityFlowState = null;
  
  // Remove the activity flow card from the DOM
  const flowCard = document.querySelector('.activity-flow-card');
  if (flowCard) {
    flowCard.remove();
  }
  
  // Don't append a message - just silently remove the card
  // The chat widget stays open for the user to continue
}

function setStatus(label) {
  const statusText = statusPill?.querySelector("span:last-child");
  if (statusText) statusText.textContent = label;
}

function getReminderTitle(reminderType, fallbackMessage) {
  const type = (reminderType || "").toLowerCase();
  if (type.includes("challenge")) return "Challenge nudge";
  if (type.includes("near_complete")) return "Almost there";
  if (type.includes("week_close")) return "Weekly check-in";
  if (type.includes("starter")) return "Fresh start";
  if (type.includes("sleep")) return "Sleep check-in";
  if (type.includes("water")) return "Hydration check-in";
  if (type.includes("mood")) return "Mood check-in";
  if (type.includes("activity")) return "Activity check-in";
  return fallbackMessage ? "Coach reminder" : "Reminder";
}

function buildReminderCard(reminder) {
  const type = (reminder.reminder_type || "").toLowerCase();

  // reminder_type → { emoji, label, theme }
  const map = [
    { key: "near_complete", emoji: "🏅", label: "Almost There!",       theme: "rc-orange" },
    { key: "week_close",    emoji: "📅", label: "Week Winding Down",    theme: "rc-blue"   },
    { key: "starter",       emoji: "🚀", label: "Let's Get Started!",   theme: "rc-green"  },
    { key: "demo",          emoji: "🔔", label: "Coach Reminder",       theme: "rc-purple" },
    { key: "mood",          emoji: "😊", label: "Mood Check",           theme: "rc-yellow" },
    { key: "activity",      emoji: "🏃", label: "Stay Active",          theme: "rc-indigo" },
    { key: "water",         emoji: "💧", label: "Hydration Check",      theme: "rc-cyan"   },
    { key: "sleep",         emoji: "😴", label: "Sleep Check",          theme: "rc-violet" },
  ];

  const cfg = map.find(m => type.includes(m.key)) || map[3]; // fallback: demo

  const now = new Date().toLocaleTimeString("en-US", {
    hour: "numeric", minute: "2-digit", hour12: true,
  });

  const card = document.createElement("div");
  card.className = `rc-card ${cfg.theme}`;
  card.dataset.reminderId = reminder.reminder_id;
  card.dataset.reminderType = reminder.reminder_type || "";
  card.innerHTML = `
    <div class="rc-header">
      <div class="rc-left">
        <div class="rc-icon-wrap">${cfg.emoji}</div>
        <span class="rc-label">${cfg.label}</span>
      </div>
      <span class="rc-time">${now}</span>
    </div>
    <p class="rc-body">${reminder.message || "You have a new reminder."}</p>
    <div class="rc-actions">
      <button class="rc-btn rc-btn-primary" data-action="take">${cfg.emoji} Take Action</button>
      <button class="rc-btn rc-btn-ghost" data-action="later">⏰ Remind Later</button>
    </div>
  `;

  const snoozePanel = document.createElement("div");
  snoozePanel.className = "rc-snooze-panel rc-snooze-hidden";
  snoozePanel.innerHTML = `
    <div class="rc-snooze-label">Remind me in</div>
    <div class="rc-snooze-grid">
      <button type="button" class="rc-snooze-option" data-snooze-minutes="15">15 min</button>
      <button type="button" class="rc-snooze-option" data-snooze-minutes="30">30 min</button>
      <button type="button" class="rc-snooze-option" data-snooze-minutes="120">2 hours</button>
      <button type="button" class="rc-snooze-option rc-snooze-custom-toggle" data-snooze-custom="true">Custom</button>
    </div>
    <div class="rc-snooze-custom rc-snooze-hidden">
      <input class="rc-snooze-input" type="number" min="5" max="1440" step="5" placeholder="Minutes" aria-label="Custom reminder minutes" />
      <div class="rc-snooze-custom-actions">
        <button type="button" class="rc-snooze-option rc-snooze-save">Save</button>
        <button type="button" class="rc-snooze-option rc-snooze-cancel">Cancel</button>
      </div>
    </div>
  `;
  card.appendChild(snoozePanel);

  // Add click handlers
  const takeBtn = card.querySelector('[data-action="take"]');
  const laterBtn = card.querySelector('[data-action="later"]');

  takeBtn.addEventListener('click', () => handleReminderCardAction(reminder, 'take', card));
  laterBtn.addEventListener('click', () => handleReminderCardAction(reminder, 'later', card));

  snoozePanel.querySelectorAll('[data-snooze-minutes]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const minutes = parseInt(btn.dataset.snoozeMinutes, 10);
      await applyReminderSnooze(reminder, minutes, card);
    });
  });

  const customToggle = snoozePanel.querySelector('[data-snooze-custom="true"]');
  const customWrap = snoozePanel.querySelector('.rc-snooze-custom');
  const customInput = snoozePanel.querySelector('.rc-snooze-input');
  const customSave = snoozePanel.querySelector('.rc-snooze-save');
  const customCancel = snoozePanel.querySelector('.rc-snooze-cancel');

  customToggle?.addEventListener('click', () => {
    customWrap.classList.remove('rc-snooze-hidden');
    customInput?.focus();
  });

  customSave?.addEventListener('click', async () => {
    const minutes = parseInt(String(customInput?.value || "").trim(), 10);
    if (!Number.isFinite(minutes) || minutes <= 0) return;
    await applyReminderSnooze(reminder, minutes, card);
  });

  customCancel?.addEventListener('click', () => {
    customWrap.classList.add('rc-snooze-hidden');
    if (customInput) customInput.value = "";
  });

  return card;
}

// Handle reminder button actions
function handleReminderAction(reminder, action, cardElement) {
  if (action === 'take') {
    // "Take Action" - dismiss the card and send a message to the agent
    cardElement.style.opacity = '0';
    cardElement.style.transform = 'scale(0.9)';
    
    setTimeout(() => {
      const row = cardElement.closest('.rc-row');
      if (row) row.remove();
    }, 300);

    // Send message to agent about taking action
    const actionMessage = `I want to take action on: ${reminder.message}`;
    appendMessage('user', actionMessage);
    
    // Optionally mark reminder as completed on backend
    if (reminder.reminder_id) {
      markReminderCompleted(reminder.reminder_id);
    }
    
  } else if (action === 'later') {
    // "Remind Later" - dismiss the card with feedback
    cardElement.style.opacity = '0';
    cardElement.style.transform = 'translateX(100px)';
    
    setTimeout(() => {
      const row = cardElement.closest('.rc-row');
      if (row) row.remove();
    }, 300);

    // Show feedback message
    appendMessage('assistant', "No problem! I'll remind you again later. 👍");
    
    // Optionally snooze reminder on backend
    if (reminder.reminder_id) {
      snoozeReminder(reminder.reminder_id);
    }
  }
}

// Mark reminder as completed on backend
async function markReminderCompleted(reminderId) {
  try {
    await fetch(`${CHALLENGE_REMINDERS_API_URL}/${reminderId}/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: USER_ID })
    });
  } catch (error) {
    console.warn('Could not mark reminder as completed:', error);
  }
}

// Snooze reminder on backend
async function snoozeReminder(reminderId, snoozeMinutes = 30) {
  try {
    await fetch(`${CHALLENGE_REMINDERS_API_URL}/${reminderId}/snooze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: USER_ID, snooze_minutes: snoozeMinutes })
    });
  } catch (error) {
    console.warn('Could not snooze reminder:', error);
  }
}

function getReminderTopic(reminderType = "", message = "") {
  const text = `${reminderType} ${message}`.toLowerCase();
  if (text.includes("sleep")) return "sleep";
  if (text.includes("water")) return "water";
  if (text.includes("mood")) return "mood";
  if (text.includes("activity")) return "activity";
  if (text.includes("step")) return "steps";
  return "challenge";
}

function removeReminderCard(cardElement, status = "done", label = "Updated") {
  if (!cardElement) return;
  const timestamp = formatReminderClock();
  const statusMeta = getReminderStatusPresentation(status);
  cardElement.dataset.reminderState = status;
  cardElement.classList.add("rc-card-acted");
  cardElement.classList.remove("rc-card-active");
  cardElement.style.opacity = "1";
  cardElement.style.transform = "none";

  const actions = cardElement.querySelector(".rc-actions, .reminder-actions");
  if (actions) {
    actions.querySelectorAll("button").forEach((button) => {
      button.disabled = true;
      button.classList.add("is-disabled");
    });
  }

  const snoozePanel = cardElement.querySelector(".rc-snooze-panel, .reminder-snooze-panel");
  if (snoozePanel) {
    snoozePanel.classList.add("rc-snooze-hidden");
    snoozePanel.classList.add("reminder-snooze-hidden");
  }

  let statusBadge = cardElement.querySelector(".rc-status-badge, .reminder-status-badge");
  if (!statusBadge) {
    statusBadge = document.createElement("div");
    statusBadge.className = "rc-status-badge reminder-status-badge";
    cardElement.appendChild(statusBadge);
  }
  statusBadge.innerHTML = `<span class="rc-status-icon">${statusMeta.icon}</span><span>${label}</span>`;

  let handledAt = cardElement.querySelector(".rc-handled-time, .reminder-handled-time");
  if (!handledAt) {
    handledAt = document.createElement("div");
    handledAt.className = "rc-handled-time reminder-handled-time";
    cardElement.appendChild(handledAt);
  }
  handledAt.textContent = `Updated at ${timestamp}`;
}

function openReminderFlow(reminderType, message) {
  const topic = getReminderTopic(reminderType, message);
  if (topic === "mood") {
    showMoodSelection();
    return;
  }
  if (topic === "activity") {
    showActivityCategories();
    return;
  }
  if (topic === "water") {
    handleShortcutClick("Log water intake");
    return;
  }
  if (topic === "sleep") {
    handleShortcutClick("Log sleep");
    return;
  }
  if (topic === "steps") {
    handleShortcutClick("Log steps");
    return;
  }
  sendMessage("Show my challenge progress");
}

function getReminderCard(reminderId) {
  return document.querySelector(`[data-reminder-id="${reminderId}"]`);
}

function hideReminderSnoozePanel(card) {
  if (!card) return;
  const snoozePanel = card.querySelector(".rc-snooze-panel, .reminder-snooze-panel");
  const customWrap = card.querySelector(".rc-snooze-custom, .reminder-snooze-custom");
  const customInput = card.querySelector(".rc-snooze-input, .reminder-snooze-input");
  if (snoozePanel) {
    snoozePanel.classList.add("rc-snooze-hidden");
    snoozePanel.classList.add("reminder-snooze-hidden");
  }
  if (customWrap) {
    customWrap.classList.add("rc-snooze-hidden");
    customWrap.classList.add("reminder-snooze-hidden");
  }
  if (customInput) customInput.value = "";
}

function showReminderSnoozePanel(card) {
  if (!card) return;
  const snoozePanel = card.querySelector(".rc-snooze-panel, .reminder-snooze-panel");
  const customWrap = card.querySelector(".rc-snooze-custom, .reminder-snooze-custom");
  const customInput = card.querySelector(".rc-snooze-input, .reminder-snooze-input");
  if (snoozePanel) {
    snoozePanel.classList.remove("rc-snooze-hidden");
    snoozePanel.classList.remove("reminder-snooze-hidden");
  }
  if (customWrap) {
    customWrap.classList.add("rc-snooze-hidden");
    customWrap.classList.add("reminder-snooze-hidden");
  }
  if (customInput) customInput.value = "";
}

async function applyReminderSnooze(reminder, minutes, cardElement) {
  const reminderId = reminder?.reminder_id;
  const snoozeMinutes = Math.min(Math.max(parseInt(minutes, 10) || 30, 5), 1440);
  if (reminderId !== undefined && reminderId !== null) {
    shownReminderIds.delete(String(reminderId));
  }
  removeReminderCard(cardElement, "snoozed", `Snoozed for ${snoozeMinutes} min`);
  appendMessage("assistant", `No problem. I’ll check back in about ${snoozeMinutes} minutes. 👌`);
  if (reminderId) {
    await snoozeReminder(reminderId, snoozeMinutes);
  }
}

async function handleReminderCardAction(reminderOrType, actionOrId, maybeAction) {
  const isObject = typeof reminderOrType === "object" && reminderOrType !== null;
  const reminderType = isObject ? (reminderOrType.reminder_type || "") : String(reminderOrType || "");
  const reminderId = isObject ? reminderOrType.reminder_id : actionOrId;
  const reminderMessage = isObject ? (reminderOrType.message || "") : "";
  const action = isObject ? actionOrId : maybeAction || "take";
  const card = getReminderCard(reminderId);

  if (action === "later") {
    const snoozeMinutes = promptSnoozeMinutes();
    if (!snoozeMinutes) return;

    removeReminderCard(card, "snoozed", "Snoozed");
    appendMessage("assistant", `No problem. I’ll check back in about ${snoozeMinutes} minutes. 👌`);

    if (reminderId) {
      await snoozeReminder(reminderId, snoozeMinutes);
    }
    return;
  }

  removeReminderCard(card, "completed", "Done");
  appendMessage("assistant", "Nice. Let’s take care of it now. 💪");
  openReminderFlow(reminderType, reminderMessage);

  if (reminderId) {
    await markReminderCompleted(reminderId);
  }
}

function appendReminderCard(reminder) {
  const key = reminder?.reminder_id ?? `${reminder?.reminder_type || "r"}:${reminder?.message || ""}`;
  if (shownReminderIds.has(String(key))) return null;
  shownReminderIds.add(String(key));

  if (!isChatOpen) updateNotificationBadge();

  const row = document.createElement("div");
  row.className = "rc-row";

  const avatar = document.createElement("div");
  avatar.className = "avatar assistant-avatar";
  avatar.textContent = "A";

  const wrap = document.createElement("div");
  wrap.className = "rc-wrap";
  wrap.appendChild(buildReminderCard(reminder));

  row.append(avatar, wrap);
  chatWindow.appendChild(row);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return row;
}

// Update notification badge count
function updateNotificationBadge() {
  let badge = chatToggleBtn.querySelector('.notification-badge');
  
  if (!badge) {
    badge = document.createElement('div');
    badge.className = 'notification-badge';
    chatToggleBtn.appendChild(badge);
  }
  
  // Count unread reminders (simple implementation)
  const currentCount = parseInt(badge.textContent) || 0;
  badge.textContent = currentCount + 1;
  
  // Add shake animation to chat button
  chatToggleBtn.classList.add('shake', 'has-notification');
  setTimeout(() => {
    chatToggleBtn.classList.remove('shake');
  }, 600);
}

// Clear notification badge when chat opens
function clearNotificationBadge() {
  const badge = chatToggleBtn.querySelector('.notification-badge');
  if (badge) {
    badge.remove();
  }
  chatToggleBtn.classList.remove('has-notification');
}

async function fetchPendingReminders() {
  try {
    const response = await fetch(`${CHALLENGE_REMINDERS_API_URL}?user_id=${USER_ID}`);
    if (!response.ok) {
      throw new Error(`Reminder request failed: ${response.status}`);
    }
    const data = await response.json();
    const reminders = Array.isArray(data.reminders) ? data.reminders : [];
    return reminders.slice(0, 1);
  } catch (error) {
    console.warn("Could not fetch reminders:", error);
    return [];
  }
}

async function fetchAndRenderReminders() {
  if (!isChatOpen) {
    return;
  }

  const reminders = await fetchPendingReminders();
  if (!reminders.length) {
    return;
  }

  appendReminderCard(reminders[0]);
}

function startReminderPolling() {
  stopReminderPolling();
  reminderPollTimer = setInterval(() => {
    if (isChatOpen) {
      fetchAndRenderReminders();
    }
  }, REMINDER_POLL_INTERVAL_MS);
}

function stopReminderPolling() {
  if (reminderPollTimer) {
    clearInterval(reminderPollTimer);
    reminderPollTimer = null;
  }
}

function isChallengeReplyText(text) {
  if (typeof text !== "string") return false;
  const normalized = text.replace(/\r?\n/g, " ").replace(/\s+/g, " ").trim();
  if (!normalized) return false;
  return /points:\s*\d+/i.test(normalized) || /\d+\s*\/\s*\d+/.test(normalized) || /badge unlocked|challenge complete/i.test(normalized);
}

function parseChallengeReplyText(text) {
  const normalized = text.replace(/\r?\n/g, " ").replace(/\s+/g, " ").trim();
  if (!normalized) return null;

  const parsed = {
    opener: "",
    points: null,
    items: [],
    celebration: null,
    encouragement: null,
    nextStep: null,
    badgeName: null,
  };

  const progressRegex = /(?:^|[\s|])(?:([🏅🎯✨👣💧😊😴🏃🔥🎉])\s*)?([^:|]{3,120}?):\s*(\d+)\s*\/\s*(\d+)(?:\s*(?:days?|logs?|steps?)\b)?/gi;
  const pointsRegex = /points:\s*(\d+)/i;
  const badgeRegex = /badge unlocked:\s*(.+)$/i;
  const pointsMatch = normalized.match(pointsRegex);
  if (pointsMatch) {
    parsed.points = Number(pointsMatch[1]);
  }

  const badgeMatch = normalized.match(badgeRegex);
  if (badgeMatch) {
    parsed.badgeName = badgeMatch[1].trim();
    parsed.celebration = `🎉 Badge unlocked: ${parsed.badgeName}`;
  } else if (/challenge complete|crushed it|nice work|great work|you nailed it|you did it/i.test(normalized)) {
    parsed.celebration = normalized.match(/(?:challenge complete|crushed it|nice work|great work|you nailed it|you did it[^.?!]*)/i)?.[0] || null;
  }

  const seen = new Set();
  let firstMarkerIndex = normalized.length;
  let lastMarkerEnd = 0;
  let match;
  while ((match = progressRegex.exec(normalized)) !== null) {
    const label = match[2].trim().replace(/\s+/g, " ");
    const normalizedLabel = label.toLowerCase();
    if (!label || normalizedLabel === "points" || seen.has(normalizedLabel)) {
      continue;
    }
    seen.add(normalizedLabel);
    const progress = Number(match[3]);
    const goal = Number(match[4]);
    const emoji = match[1] || getChallengeEmoji(label);
    parsed.items.push({ label, progress, goal, emoji });
    firstMarkerIndex = Math.min(firstMarkerIndex, match.index);
    lastMarkerEnd = Math.max(lastMarkerEnd, progressRegex.lastIndex);
  }

  const openerSource = parsed.items.length || parsed.points !== null || parsed.celebration
    ? normalized.slice(0, firstMarkerIndex).trim()
    : normalized;
  parsed.opener = openerSource.replace(/[:\-–|]+$/, "").trim() || "Let’s keep the streak moving.";

  const tail = normalized.slice(lastMarkerEnd).trim();
  if (tail) {
    const cleanTail = tail.replace(/^[|,.\s]+/, "").trim();
    if (/^(keep|nice|great|awesome|let|you|small|one)/i.test(cleanTail)) {
      parsed.encouragement = cleanTail;
    } else if (!parsed.celebration && cleanTail) {
      parsed.encouragement = cleanTail;
    } else {
      parsed.nextStep = cleanTail;
    }
  }

  if (!parsed.encouragement) {
    parsed.encouragement = parsed.badgeName ? "Keep the momentum going." : "Nice progress. Keep going.";
  }

  return parsed.items.length || parsed.points !== null || parsed.celebration ? parsed : null;
}

function getChallengeEmoji(label) {
  const normalized = (label || "").toLowerCase();
  if (normalized.includes("mood")) return "😊";
  if (normalized.includes("sleep")) return "😴";
  if (normalized.includes("step")) return "👣";
  if (normalized.includes("water")) return "💧";
  if (normalized.includes("activity")) return "🏃";
  return "✨";
}

function buildChallengeReplyCard(parsed) {
  const card = document.createElement("div");
  card.className = `challenge-summary-card ${parsed.celebration ? "challenge-summary-card-complete" : ""}`.trim();

  const header = document.createElement("div");
  header.className = "challenge-summary-header";

  const titleWrap = document.createElement("div");
  titleWrap.className = "challenge-summary-title-wrap";

  const kicker = document.createElement("div");
  kicker.className = "challenge-summary-kicker";
  kicker.textContent = "Coach check-in";

  const title = document.createElement("div");
  title.className = "challenge-summary-title";
  title.textContent = parsed.opener || "Let’s keep the streak moving.";

  titleWrap.append(kicker, title);

  const headerBadge = document.createElement("div");
  headerBadge.className = "challenge-summary-badge";
  headerBadge.textContent = parsed.celebration ? (parsed.badgeName || "Badge unlocked") : "Progress";

  header.append(titleWrap, headerBadge);
  card.appendChild(header);

  const stats = document.createElement("div");
  stats.className = "challenge-summary-stats";

  const pointsTile = document.createElement("div");
  pointsTile.className = "challenge-stat-tile";
  const pointsLabel = document.createElement("span");
  pointsLabel.className = "challenge-stat-label";
  pointsLabel.textContent = "Points";
  const pointsValue = document.createElement("strong");
  pointsValue.className = "challenge-stat-value";
  pointsValue.textContent = parsed.points !== null ? String(parsed.points) : "0";
  pointsTile.append(pointsLabel, pointsValue);
  stats.appendChild(pointsTile);

  if (parsed.items.length) {
    const completedCount = parsed.items.filter((item) => item.progress >= item.goal).length;
    const totalCount = parsed.items.length;
    const completionTile = document.createElement("div");
    completionTile.className = "challenge-stat-tile";
    const completionLabel = document.createElement("span");
    completionLabel.className = "challenge-stat-label";
    completionLabel.textContent = "Done";
    const completionValue = document.createElement("strong");
    completionValue.className = "challenge-stat-value";
    completionValue.textContent = `${completedCount}/${totalCount}`;
    completionTile.append(completionLabel, completionValue);
    stats.appendChild(completionTile);
  }

  card.appendChild(stats);

  const grid = document.createElement("div");
  grid.className = "challenge-progress-grid";

  parsed.items.forEach((item) => {
    const tile = document.createElement("div");
    tile.className = "challenge-progress-tile";
    if (item.progress >= item.goal) {
      tile.classList.add("done");
    }

    const row = document.createElement("div");
    row.className = "challenge-progress-row";

    const label = document.createElement("div");
    label.className = "challenge-progress-label";
    label.textContent = `${item.emoji} ${item.label}`;

    const value = document.createElement("div");
    value.className = "challenge-progress-value";
    value.textContent = `${item.progress}/${item.goal}`;

    row.append(label, value);

    const bar = document.createElement("div");
    bar.className = "challenge-progress-bar";

    const fill = document.createElement("div");
    fill.className = "challenge-progress-fill";
    const ratio = item.goal > 0 ? Math.min((item.progress / item.goal) * 100, 100) : 0;
    fill.style.width = `${ratio}%`;
    bar.appendChild(fill);

    tile.append(row, bar);
    grid.appendChild(tile);
  });

  if (grid.childElementCount) {
    card.appendChild(grid);
  }

  if (parsed.celebration) {
    const celebration = document.createElement("div");
    celebration.className = "challenge-celebration";
    celebration.textContent = parsed.celebration;
    card.appendChild(celebration);
  }

  const footer = document.createElement("div");
  footer.className = "challenge-summary-footer";
  footer.textContent = parsed.nextStep || parsed.encouragement || "Keep going today with one small win.";
  card.appendChild(footer);

  return card;
}

// ============================================================
// CONTENT SUGGESTIONS RENDERING
// ============================================================

function parseContentSuggestions(text) {
  // Detect if message contains content suggestions
  // Multiple formats supported:
  // Format 1: 1. Title (duration) - description [Watch here](url)
  // Format 2: 1. [Title](url) (Type, duration) - description
  // Format 3: 1. **Title** (duration) description [Watch here](url) (no dash)
  
  const hasNumberedList = /\d+\.\s+/.test(text);
  const hasLinks = /\[.+?\]\(https?:\/\/[^\)]+\)/i.test(text);
  
  if (!hasNumberedList || !hasLinks) {
    return null;
  }
  
  // Extract intro text (before first numbered item)
  const introMatch = text.match(/^(.*?)(?=\d+\.\s+)/s);
  const intro = introMatch ? introMatch[1].trim() : "";
  
  const suggestions = [];
  
  // Try Format 2 first: 1. [Title](url) (Type, duration) - description
  const format2Pattern = /(\d+)\.\s+\[([^\]]+)\]\((https?:\/\/[^\)]+)\)\s+\(([^,]+),\s*~?(\d+)\s*min\)\s+-\s+(.+?)(?=\d+\.\s+\[|Would you like|$)/gs;
  let match;
  
  while ((match = format2Pattern.exec(text)) !== null) {
    suggestions.push({
      number: parseInt(match[1]),
      title: match[2].trim(),
      url: match[3].trim(),
      type: match[4].trim(),
      duration: match[5].trim() + " min",
      description: match[6].trim()
    });
  }
  
  // If Format 2 didn't match, try Format 1: 1. Title (duration) - description [Watch here](url)
  if (suggestions.length === 0) {
    const format1Pattern = /(\d+)\.\s+\*{0,2}([^(*\n]+?)\*{0,2}\s+\(([^)]+)\)\s+-\s+([^\[]+?)\s*\[(?:Watch|Listen|Read) here\]\((https?:\/\/[^\)]+)\)/gi;
    
    while ((match = format1Pattern.exec(text)) !== null) {
      suggestions.push({
        number: parseInt(match[1]),
        title: match[2].trim(),
        duration: match[3].trim(),
        description: match[4].trim(),
        url: match[5].trim()
      });
    }
  }
  
  // If still no match, try Format 3: 1. **Title** (duration) description [Watch here](url) (no dash)
  if (suggestions.length === 0) {
    const format3Pattern = /(\d+)\.\s+\*{0,2}([^(*\n]+?)\*{0,2}\s+\(([^)]+)\)\s+([^\[]+?)\s*\[(?:Watch|Listen|Read) here\]\((https?:\/\/[^\)]+)\)/gi;
    
    while ((match = format3Pattern.exec(text)) !== null) {
      suggestions.push({
        number: parseInt(match[1]),
        title: match[2].trim(),
        duration: match[3].trim(),
        description: match[4].trim(),
        url: match[5].trim()
      });
    }
  }
  
  if (suggestions.length === 0) {
    return null;
  }
  
  // Extract outro text (after last suggestion)
  const lastLinkIndex = text.lastIndexOf('](');
  if (lastLinkIndex !== -1) {
    const afterLastLink = text.indexOf(')', lastLinkIndex) + 1;
    const outro = text.substring(afterLastLink).trim();
    
    return {
      intro,
      suggestions,
      outro
    };
  }
  
  return {
    intro,
    suggestions,
    outro: ""
  };
}

function createContentSuggestionCard(suggestion, index, totalCount) {
  const card = document.createElement("div");
  card.className = "content-suggestion-card";
  card.dataset.suggestionIndex = index;
  
  // Icon based on content type (infer from URL or duration)
  let icon = "🎬";
  const url = suggestion.url.toLowerCase();
  if (url.includes("youtube") || url.includes("youtu.be")) {
    icon = "🎬";
  } else if (url.includes("spotify") || url.includes("music") || suggestion.title.toLowerCase().includes("music")) {
    icon = "🎵";
  } else if (url.includes("article") || url.includes("blog") || url.includes("vantagefit")) {
    icon = "📰";
  }
  
  card.innerHTML = `
    <div class="content-suggestion-header">
      <span class="content-suggestion-icon">${icon}</span>
      <div class="content-suggestion-title-wrap">
        <h4 class="content-suggestion-title">${suggestion.title}</h4>
        <span class="content-suggestion-duration">${suggestion.duration}</span>
      </div>
    </div>
    <p class="content-suggestion-description">${suggestion.description}</p>
    <button class="content-suggestion-btn" data-url="${suggestion.url}">
      <span class="content-suggestion-btn-icon">▶</span>
      <span class="content-suggestion-btn-text">Try This</span>
    </button>
  `;
  
  // Add click handler
  const button = card.querySelector(".content-suggestion-btn");
  button.addEventListener("click", () => {
    handleSuggestionClick(card, suggestion.url, totalCount);
  });
  
  return card;
}

function handleSuggestionClick(clickedCard, url, totalCount) {
  const container = clickedCard.closest(".content-suggestions-container");
  if (!container) return;
  
  // Disable all other cards
  const allCards = container.querySelectorAll(".content-suggestion-card");
  allCards.forEach(card => {
    if (card !== clickedCard) {
      card.classList.add("disabled");
      const btn = card.querySelector(".content-suggestion-btn");
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="content-suggestion-btn-text">Not Selected</span>';
      }
    }
  });
  
  // Mark clicked card as selected
  clickedCard.classList.add("selected");
  const clickedBtn = clickedCard.querySelector(".content-suggestion-btn");
  if (clickedBtn) {
    clickedBtn.innerHTML = '<span class="content-suggestion-btn-icon">✓</span><span class="content-suggestion-btn-text">Selected</span>';
    clickedBtn.disabled = true;
  }
  
  // Open URL in new tab
  window.open(url, "_blank");
  
  // TODO: Track interaction in backend
  // trackContentInteraction(suggestion.id, "clicked");
}

function renderContentSuggestions(parsed) {
  const wrapper = document.createElement("div");
  wrapper.className = "content-suggestions-wrapper";
  
  // Intro text
  if (parsed.intro) {
    const intro = document.createElement("p");
    intro.className = "content-suggestions-intro";
    intro.textContent = parsed.intro;
    wrapper.appendChild(intro);
  }
  
  // Suggestions container
  const container = document.createElement("div");
  container.className = "content-suggestions-container";
  
  parsed.suggestions.forEach((suggestion, index) => {
    const card = createContentSuggestionCard(suggestion, index, parsed.suggestions.length);
    container.appendChild(card);
  });
  
  wrapper.appendChild(container);
  
  // Outro text
  if (parsed.outro) {
    const outro = document.createElement("p");
    outro.className = "content-suggestions-outro";
    outro.textContent = parsed.outro;
    wrapper.appendChild(outro);
  }
  
  return wrapper;
}

function appendMessage(role, text, options = {}) {
  // Check for content suggestions first
  if (role === "assistant" && typeof text === "string") {
    const parsedSuggestions = parseContentSuggestions(text);
    if (parsedSuggestions) {
      return appendMessageElement("assistant", renderContentSuggestions(parsedSuggestions), {
        ...options,
        messageClass: ["content-suggestions-message", options.messageClass].filter(Boolean).join(" "),
        bubbleClass: ["content-suggestions-bubble", options.bubbleClass].filter(Boolean).join(" "),
      });
    }
  }
  
  // Check for challenge reply
  if (role === "assistant" && typeof text === "string") {
    const parsedChallenge = isChallengeReplyText(text) ? parseChallengeReplyText(text) : null;
    if (parsedChallenge) {
      return appendMessageElement("assistant", buildChallengeReplyCard(parsedChallenge), {
        ...options,
        messageClass: ["challenge-message", options.messageClass].filter(Boolean).join(" "),
        bubbleClass: ["challenge-bubble", options.bubbleClass].filter(Boolean).join(" "),
      });
    }
  }

  if (typeof text === "string" || text instanceof Node) {
    return appendMessageElement(role, text, options);
  }

  return appendMessageElement(role, String(text), options);
}

function addTypingIndicator() {
  const wrapper = document.createElement("div");
  wrapper.className = "message assistant";
  wrapper.id = "typingIndicator";

  const avatar = document.createElement("div");
  avatar.className = "avatar assistant-avatar";
  avatar.textContent = "A";

  const stack = document.createElement("div");
  stack.className = "message-stack";

  const meta = document.createElement("div");
  meta.className = "message-meta";

  const name = document.createElement("p");
  name.className = "message-name";
  name.textContent = "FitCoach Assistant";

  meta.appendChild(name);

  const bubble = document.createElement("div");
  bubble.className = "bubble assistant-bubble typing-bubble";

  const thinkingText = document.createElement("div");
  thinkingText.className = "typing-thinking-text";
  thinkingText.textContent = "Agent is analyzing your data...";

  const indicator = document.createElement("div");
  indicator.className = "typing-indicator";
  indicator.innerHTML = "<span></span><span></span><span></span>";

  bubble.append(thinkingText, indicator);
  stack.append(meta, bubble);
  wrapper.append(avatar, stack);
  chatWindow.appendChild(wrapper);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function removeTypingIndicator() {
  const indicator = document.getElementById("typingIndicator");
  if (indicator) {
    indicator.remove();
  }
}

async function sendMessage(message) {
  const trimmed = message.trim();
  if (!trimmed) return;

  appendMessage("user", trimmed);
  messageInput.value = "";
  autoResizeTextarea();

  sendButton.disabled = true;
  setStatus("Thinking");
  addTypingIndicator();

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: trimmed,
        user_id: USER_ID,
      }),
    });

    removeTypingIndicator();

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    const data = await response.json();
    appendMessage("assistant", data.reply || "I could not form a response just now.");
    setStatus("Connected");
    refreshDashboardViews();
    if (isChatOpen) {
      fetchAndRenderReminders();
    }
  } catch (error) {
    removeTypingIndicator();
    appendMessage(
      "assistant",
      "I could not reach the backend just now. Make sure FastAPI is running and refresh the page."
    );
    setStatus("Connection issue");
    console.error(error);
  } finally {
    sendButton.disabled = false;
    messageInput.focus();
  }
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await sendMessage(messageInput.value);
});

messageInput.addEventListener("input", autoResizeTextarea);
messageInput.addEventListener("keydown", async (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    await sendMessage(messageInput.value);
  }
});

// Toggle chat widget
chatToggleBtn?.addEventListener("click", toggleChat);

// Log Activity button
logActivityBtn?.addEventListener("click", (e) => {
  e.preventDefault();
  showActivityCategories();
});

// Log Mood button
logMoodBtn?.addEventListener("click", (e) => {
  e.preventDefault();
  showMoodSelection();
});

// Log Meal button
logMealBtn?.addEventListener("click", (e) => {
  e.preventDefault();
  showMealLogging();
});

dashboardRefreshBtn?.addEventListener("click", (event) => {
  event.preventDefault();
  loadDashboard();
});

// Handle shortcut clicks - Updated selector for inline shortcuts
document.addEventListener("click", (event) => {
  const dashboardPromptBtn = event.target.closest("[data-dashboard-prompt]");
  if (dashboardPromptBtn) {
    const prompt = dashboardPromptBtn.dataset.dashboardPrompt;
    if (prompt) {
      if (!isChatOpen) {
        toggleChat();
      }
      sendMessage(prompt);
    }
    return;
  }

  const shortcutBtn = event.target.closest(".shortcut-btn-inline:not(.shortcut-activity)");
  if (shortcutBtn) {
    const shortcutText = shortcutBtn.dataset.shortcut;
    if (shortcutText) {
      handleShortcutClick(shortcutText);
    }
  }
});

// Close chat when clicking outside
document.addEventListener("click", (event) => {
  if (isChatOpen && 
      !chatWidget.contains(event.target) && 
      !chatToggleBtn.contains(event.target)) {
    toggleChat();
  }
});

autoResizeTextarea();
loadDashboard();


// ========== PROACTIVE REMINDER FUNCTIONS ==========

async function fetchReminders() {
  try {
    const response = await fetch(`${CHALLENGE_REMINDERS_API_URL}?user_id=${USER_ID}`);
    if (!response.ok) {
      throw new Error('Failed to fetch reminders');
    }
    const data = await response.json();
    return data.reminders || [];
  } catch (error) {
    console.error('Error fetching reminders:', error);
    return [];
  }
}

function getReminderTypeClass(reminderType) {
  const typeMap = {
    'mood': 'reminder-mood',
    'activity': 'reminder-activity',
    'water': 'reminder-water',
    'sleep': 'reminder-mood',
    'steps': 'reminder-activity'
  };
  return typeMap[reminderType] || '';
}

function getReminderIcon(reminderType) {
  const iconMap = {
    'mood': '😊',
    'activity': '🏃',
    'water': '💧',
    'sleep': '😴',
    'steps': '👟'
  };
  return iconMap[reminderType] || '💡';
}

function getReminderActionText(reminderType) {
  const actionMap = {
    'mood': 'Log Mood',
    'activity': 'Log Activity',
    'water': 'Log Water',
    'sleep': 'Log Sleep',
    'steps': 'Track Steps'
  };
  return actionMap[reminderType] || 'Take Action';
}

function getReminderStatusPresentation(status = "pending") {
  const normalized = String(status || "pending").toLowerCase();
  if (normalized === "completed") {
    return { icon: "✅", label: "Done", tone: "completed" };
  }
  if (normalized === "snoozed") {
    return { icon: "⏳", label: "Snoozed", tone: "snoozed" };
  }
  return { icon: "✨", label: "Pending", tone: "pending" };
}

function formatReminderClock(value = new Date()) {
  const date = value instanceof Date ? value : new Date(value);
  return date.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

function formatReminderDate(value = new Date()) {
  const date = value instanceof Date ? value : new Date(value);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function createReminderCard(reminder) {
  const card = document.createElement('div');
  const typeClass = getReminderTypeClass(reminder.reminder_type);
  card.className = `reminder-card ${typeClass}`;
  card.dataset.reminderId = reminder.reminder_id;
  card.dataset.reminderState = reminder.status || "pending";
  
  const icon = getReminderIcon(reminder.reminder_type);
  const actionText = getReminderActionText(reminder.reminder_type);
  const statusMeta = getReminderStatusPresentation(reminder.status);
  const createdLabel = reminder.sent_at
    ? `Sent ${formatReminderClock(reminder.sent_at)}`
    : `Seen ${formatReminderClock()}`;
  
  card.innerHTML = `
    <div class="reminder-kicker">
      <span class="reminder-kicker-icon">✨</span>
      Proactive Coach
    </div>
    <div class="reminder-header">
      <h4 class="reminder-title">Time for a quick check-in</h4>
      <span class="reminder-badge">
        <span class="reminder-badge-icon">${icon}</span>
        ${reminder.reminder_type}
      </span>
    </div>
    <p class="reminder-message">${reminder.message}</p>
    <div class="reminder-meta-row">
      <span class="reminder-meta-chip">${createdLabel}</span>
      <span class="reminder-meta-chip reminder-meta-state reminder-meta-${statusMeta.tone}">
        <span class="reminder-meta-icon">${statusMeta.icon}</span>
        ${statusMeta.label}
      </span>
    </div>
    <div class="reminder-actions">
      <button class="reminder-action-btn" onclick="handleReminderCardAction('${reminder.reminder_type}', ${reminder.reminder_id}, 'take')">
        <span class="reminder-action-icon">${icon}</span>
        ${actionText}
      </button>
      <button class="reminder-action-btn reminder-dismiss-btn" onclick="handleReminderCardAction('${reminder.reminder_type}', ${reminder.reminder_id}, 'later')">
        Later
      </button>
    </div>
  `;

  const snoozePanel = document.createElement('div');
  snoozePanel.className = 'reminder-snooze-panel reminder-snooze-hidden';
  snoozePanel.innerHTML = `
    <div class="reminder-snooze-label">Remind me in</div>
    <div class="reminder-snooze-grid">
      <button type="button" class="reminder-snooze-option" data-snooze-minutes="15">15 min</button>
      <button type="button" class="reminder-snooze-option" data-snooze-minutes="30">30 min</button>
      <button type="button" class="reminder-snooze-option" data-snooze-minutes="120">2 hours</button>
      <button type="button" class="reminder-snooze-option reminder-snooze-custom-toggle" data-snooze-custom="true">Custom</button>
    </div>
    <div class="reminder-snooze-custom reminder-snooze-hidden">
      <input class="reminder-snooze-input" type="number" min="5" max="1440" step="5" placeholder="Minutes" aria-label="Custom reminder minutes" />
      <div class="reminder-snooze-custom-actions">
        <button type="button" class="reminder-snooze-option reminder-snooze-save">Save</button>
        <button type="button" class="reminder-snooze-option reminder-snooze-cancel">Cancel</button>
      </div>
    </div>
  `;
  card.appendChild(snoozePanel);

  snoozePanel.querySelectorAll('[data-snooze-minutes]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const minutes = parseInt(btn.dataset.snoozeMinutes, 10);
      await applyReminderSnooze(reminder, minutes, card);
    });
  });

  const customToggle = snoozePanel.querySelector('[data-snooze-custom="true"]');
  const customWrap = snoozePanel.querySelector('.reminder-snooze-custom');
  const customInput = snoozePanel.querySelector('.reminder-snooze-input');
  const customSave = snoozePanel.querySelector('.reminder-snooze-save');
  const customCancel = snoozePanel.querySelector('.reminder-snooze-cancel');

  customToggle?.addEventListener('click', () => {
    customWrap.classList.remove('reminder-snooze-hidden');
    customInput?.focus();
  });

  customSave?.addEventListener('click', async () => {
    const minutes = parseInt(String(customInput?.value || "").trim(), 10);
    if (!Number.isFinite(minutes) || minutes <= 0) return;
    await applyReminderSnooze(reminder, minutes, card);
  });

  customCancel?.addEventListener('click', () => {
    customWrap.classList.add('reminder-snooze-hidden');
    if (customInput) customInput.value = "";
  });

  return card;
}

function showReminder(reminder) {
  // Check if reminder already exists
  const existing = document.querySelector(`[data-reminder-id="${reminder.reminder_id}"]`);
  if (existing) {
    return;
  }
  
  const card = createReminderCard(reminder);
  chatWindow.appendChild(card);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function showReminders(reminders) {
  if (!reminders || reminders.length === 0) {
    return;
  }
  
  // Show only the first reminder to avoid overwhelming the user
  showReminder(reminders[0]);
}

async function handleReminderAction(reminderType, reminderId) {
  // Dismiss the reminder first
  dismissReminder(reminderId);
  
  // Trigger the appropriate action
  switch(reminderType) {
    case 'mood':
      showMoodSelection();
      break;
    case 'activity':
      showActivityCategories();
      break;
    case 'water':
      handleShortcutClick('Log water intake');
      break;
    case 'sleep':
      handleShortcutClick('Log sleep');
      break;
    case 'steps':
      handleShortcutClick('Log steps');
      break;
    default:
      console.warn('Unknown reminder type:', reminderType);
  }
}

function dismissReminder(reminderId) {
  const card = document.querySelector(`[data-reminder-id="${reminderId}"]`);
  if (card) {
    card.style.opacity = '0';
    card.style.transform = 'translateY(-10px)';
    setTimeout(() => card.remove(), 300);
  }
  
  // Optionally, mark as dismissed on backend
  markReminderAsDismissed(reminderId);
}

async function markReminderAsDismissed(reminderId) {
  try {
    await fetch(`${CHALLENGE_REMINDERS_API_URL}/${reminderId}/dismiss`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ user_id: USER_ID })
    });
  } catch (error) {
    console.warn('Could not mark reminder as dismissed:', error);
  }
}

async function checkForReminders() {
  const reminders = await fetchReminders();
  showReminders(reminders);
}

async function handleReminderCardAction(reminderOrType, actionOrId, maybeAction) {
  const isObject = typeof reminderOrType === "object" && reminderOrType !== null;
  const reminderType = isObject ? (reminderOrType.reminder_type || "") : String(reminderOrType || "");
  const reminderId = isObject ? reminderOrType.reminder_id : actionOrId;
  const reminderMessage = isObject ? (reminderOrType.message || "") : "";
  const action = isObject ? actionOrId : maybeAction || "take";
  const card = getReminderCard(reminderId);

  if (action === "later") {
    if (!card) return;
    const snoozePanel = card.querySelector(".rc-snooze-panel, .reminder-snooze-panel");
    const isOpen = snoozePanel && !snoozePanel.classList.contains("rc-snooze-hidden") && !snoozePanel.classList.contains("reminder-snooze-hidden");
    if (isOpen) {
      hideReminderSnoozePanel(card);
    } else if (snoozePanel) {
      showReminderSnoozePanel(card);
    }
    return;
  }

  removeReminderCard(card, "completed", "Done");
  appendMessage("assistant", "Nice. Let’s take care of it now. 💪");
  openReminderFlow(reminderType, reminderMessage);

  if (reminderId) {
    await markReminderCompleted(reminderId);
  }
}

async function handleReminderCardAction(reminderOrType, actionOrId, maybeAction) {
  const isObject = typeof reminderOrType === "object" && reminderOrType !== null;
  const reminderType = isObject ? (reminderOrType.reminder_type || "") : String(reminderOrType || "");
  const reminderId = isObject ? reminderOrType.reminder_id : actionOrId;
  const reminderMessage = isObject ? (reminderOrType.message || "") : "";
  const action = isObject ? actionOrId : maybeAction || "take";
  const card = getReminderCard(reminderId);

  if (!card) return;

  if (action === "later") {
    const snoozePanel = card.querySelector(".rc-snooze-panel, .reminder-snooze-panel");
    const isOpen = snoozePanel && !snoozePanel.classList.contains("rc-snooze-hidden") && !snoozePanel.classList.contains("reminder-snooze-hidden");
    if (isOpen) {
      hideReminderSnoozePanel(card);
    } else if (snoozePanel) {
      showReminderSnoozePanel(card);
    }
    return;
  }

  removeReminderCard(card, "completed", "Completed");
  appendMessage("assistant", "Nice. Let’s take care of it now. 💪");
  openReminderFlow(reminderType, reminderMessage);

  if (reminderId) {
    await markReminderCompleted(reminderId);
  }
}

// ========== END PROACTIVE REMINDER FUNCTIONS ==========

// Native HTML5 time picker is used - no custom picker code needed
