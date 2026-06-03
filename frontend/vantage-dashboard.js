// Vantage Dashboard - Backend Integration
const API_BASE = '/api/v1';
// User id comes from page config, with a compatibility fallback for chat.js.

// State
let selectedDate = new Date();
let dashboardData = null;
let currentSlide = 0;
let carouselInterval = null;
let dashboardRequestController = null;
let dashboardRequestId = 0;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  initializeTabs();
  initializeDateSelector();
  initializeCarousel();

  await detectAndSetUserTimezone();

  loadDashboardData({ showLoading: true });

  setupEventListeners();
  startAutoRefresh();
  initializeSuggestionCards();
});

// Tab Switching
function initializeTabs() {
  const tabButtons = document.querySelectorAll('.tab-pill');
  
  tabButtons.forEach(button => {
    button.addEventListener('click', () => {
      const tabName = button.getAttribute('data-tab');
      switchTab(tabName);
      
      // Update active state
      tabButtons.forEach(btn => btn.classList.remove('active'));
      button.classList.add('active');
    });
  });
  
  // Initialize challenge tabs
  const challengeTabs = document.querySelectorAll('.challenge-tab');
  challengeTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const challengeTabName = tab.getAttribute('data-challenge-tab');
      switchChallengeTab(challengeTabName);
      
      // Update active state
      challengeTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
    });
  });
}

function switchTab(tabName) {
  // Hide all tab contents
  document.querySelectorAll('.tab-content').forEach(content => {
    content.classList.remove('active');
  });
  
  // Show selected tab content
  if (tabName === 'activity') {
    document.getElementById('activityContent').classList.add('active');
  } else if (tabName === 'challenges') {
    document.getElementById('challengesContent').classList.add('active');
    loadChallenges();
  }
}

function switchChallengeTab(tabName) {
  // Hide all challenge tab contents
  document.querySelectorAll('.challenge-tab-content').forEach(content => {
    content.classList.remove('active');
  });
  
  // Show selected challenge tab content
  if (tabName === 'ongoing') {
    document.getElementById('ongoingChallenges').classList.add('active');
  } else if (tabName === 'upcoming') {
    document.getElementById('upcomingChallenges').classList.add('active');
  } else if (tabName === 'past') {
    document.getElementById('pastChallenges').classList.add('active');
  }
}

// Load Challenges
async function loadChallenges() {
  try {
    const response = await fetch(`${API_BASE}/challenges?user_id=${getDashboardUserId()}`);
    const data = await response.json();
    
    // Separate challenges by status
    const ongoing = data.challenges?.filter(c => c.status === 'ongoing') || [];
    const upcoming = data.challenges?.filter(c => c.status === 'upcoming') || [];
    const past = data.challenges?.filter(c => c.status === 'past' || c.status === 'completed') || [];
    
    // Populate ongoing challenges
    const ongoingGrid = document.getElementById('ongoingGrid');
    if (ongoing.length > 0) {
      ongoingGrid.innerHTML = ongoing.map(challenge => createChallengeCard(challenge)).join('');
    } else {
      ongoingGrid.innerHTML = '<div class="challenge-empty-message"><p>There are no Ongoing challenges available.</p></div>';
    }
    
    // Populate upcoming challenges
    const upcomingGrid = document.getElementById('upcomingGrid');
    if (upcoming.length > 0) {
      upcomingGrid.innerHTML = upcoming.map(challenge => createChallengeCard(challenge)).join('');
    } else {
      upcomingGrid.innerHTML = '<div class="challenge-empty-message"><p>There are no Upcoming challenges available.</p></div>';
    }
    
    // Populate past challenges
    const pastGrid = document.getElementById('pastGrid');
    if (past.length > 0) {
      pastGrid.innerHTML = past.map(challenge => createChallengeCard(challenge)).join('');
    } else {
      pastGrid.innerHTML = '<div class="challenge-empty-message"><p>There are no Past challenges available.</p></div>';
    }
  } catch (error) {
    console.error('Error loading challenges:', error);
    document.getElementById('ongoingGrid').innerHTML = '<div class="challenge-empty-message"><p>Failed to load challenges.</p></div>';
  }
}

function createChallengeCard(challenge) {
  return `
    <div class="dashboard-card challenge-card">
      <h3>${challenge.title}</h3>
      <p>${challenge.description}</p>
      <div class="challenge-progress">
        <div class="progress-bar">
          <div class="progress-fill" style="width: ${challenge.progress || 0}%"></div>
        </div>
        <span>${challenge.progress || 0}% Complete</span>
      </div>
    </div>
  `;
}

// Hero Banner Carousel
let carouselInitialized = false;

function initializeCarousel() {
  if (carouselInitialized) return;
  
  const track = document.getElementById('carouselTrack');
  const slides = document.querySelectorAll('.carousel-slide');
  const indicators = document.querySelectorAll('.indicator');
  const prevBtn = document.getElementById('carouselPrev');
  const nextBtn = document.getElementById('carouselNext');
  
  if (!track) {
    console.error('Carousel track not found');
    return;
  }
  
  if (slides.length === 0) {
    console.error('No carousel slides found');
    return;
  }
  
  console.log('Initializing carousel with', slides.length, 'slides');
  carouselInitialized = true;
  
  // Set initial state
  currentSlide = 0;
  updateCarousel();
  
  // Previous button
  if (prevBtn) {
    prevBtn.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      
      if (currentSlide > 0) {
        console.log('Prev clicked - current:', currentSlide);
        currentSlide = currentSlide - 1;
        updateCarousel();
        resetAutoPlay();
      }
    });
  }
  
  // Next button
  if (nextBtn) {
    nextBtn.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      
      if (currentSlide < slides.length - 1) {
        console.log('Next clicked - current:', currentSlide);
        currentSlide = currentSlide + 1;
        updateCarousel();
        resetAutoPlay();
      }
    });
  }
  
  // Indicator buttons
  indicators.forEach((indicator, index) => {
    indicator.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      console.log('Indicator clicked:', index);
      currentSlide = index;
      updateCarousel();
      resetAutoPlay();
    });
  });
  
  // Start auto-play
  startAutoPlay();
  
  // Pause on hover
  const carousel = document.querySelector('.hero-banner-carousel');
  if (carousel) {
    carousel.addEventListener('mouseenter', pauseAutoPlay);
    carousel.addEventListener('mouseleave', startAutoPlay);
  }
}

function updateCarousel() {
  const track = document.getElementById('carouselTrack');
  const slides = document.querySelectorAll('.carousel-slide');
  const indicators = document.querySelectorAll('.indicator');
  const prevBtn = document.getElementById('carouselPrev');
  const nextBtn = document.getElementById('carouselNext');
  
  if (!track || slides.length === 0) return;
  
  console.log('Updating carousel to slide:', currentSlide);
  
  // Calculate and apply transform
  const offset = -(currentSlide * 100);
  track.style.transform = `translateX(${offset}%)`;
  
  console.log('Transform applied:', track.style.transform);
  
  // Update active classes
  slides.forEach((slide, i) => {
    if (i === currentSlide) {
      slide.classList.add('active');
    } else {
      slide.classList.remove('active');
    }
  });
  
  indicators.forEach((indicator, i) => {
    if (i === currentSlide) {
      indicator.classList.add('active');
    } else {
      indicator.classList.remove('active');
    }
  });
  
  // Update button states
  if (prevBtn) {
    if (currentSlide === 0) {
      prevBtn.disabled = true;
      prevBtn.setAttribute('aria-disabled', 'true');
    } else {
      prevBtn.disabled = false;
      prevBtn.setAttribute('aria-disabled', 'false');
    }
  }
  
  if (nextBtn) {
    if (currentSlide === slides.length - 1) {
      nextBtn.disabled = true;
      nextBtn.setAttribute('aria-disabled', 'true');
    } else {
      nextBtn.disabled = false;
      nextBtn.setAttribute('aria-disabled', 'false');
    }
  }
}

function goToSlide(index) {
  const slides = document.querySelectorAll('.carousel-slide');
  if (slides.length === 0) return;
  
  // Clamp to valid range (no wrapping)
  if (index < 0) {
    currentSlide = 0;
  } else if (index >= slides.length) {
    currentSlide = slides.length - 1;
  } else {
    currentSlide = index;
  }
  
  updateCarousel();
}

function startAutoPlay() {
  if (carouselInterval) return;
  console.log('Starting carousel auto-play');
  carouselInterval = setInterval(() => {
    const slides = document.querySelectorAll('.carousel-slide');
    if (slides.length > 0) {
      // Auto-play wraps around
      if (currentSlide < slides.length - 1) {
        currentSlide = currentSlide + 1;
      } else {
        currentSlide = 0; // Loop back to first slide
      }
      updateCarousel();
    }
  }, 3000); // Auto-play every 3 seconds
}

function pauseAutoPlay() {
  if (carouselInterval) {
    console.log('Pausing carousel auto-play');
    clearInterval(carouselInterval);
    carouselInterval = null;
  }
}

function resetAutoPlay() {
  pauseAutoPlay();
  setTimeout(startAutoPlay, 100);
}

// Date Selector
let dateOffset = 0; // Track the offset from today (in days backward)

function initializeDateSelector() {
  const dateSelector = document.getElementById('dateSelector');
  const dates = generateDateRange(8); // Show 8 days
  
  dateSelector.innerHTML = dates.map((date, index) => {
    const isSelected = isSameDay(date, selectedDate);
    return `
      <div class="date-card ${isSelected ? 'selected' : ''}" data-date="${date.toISOString()}">
        <div class="date-day">${formatDay(date)}</div>
        <div class="date-number">${date.getDate().toString().padStart(2, '0')}</div>
      </div>
    `;
  }).join('');
  
  // Add click listeners
  dateSelector.querySelectorAll('.date-card').forEach(card => {
    card.addEventListener('click', () => {
      const dateStr = card.dataset.date;
      selectedDate = new Date(dateStr);
      updateDateSelector();
      updateTodayLabel();
      loadDashboardData({ showLoading: true });
    });
  });
  
  updateTodayLabel();
  updateNavigationButtons();
}

function generateDateRange(days) {
  const dates = [];
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  // Calculate the end date (today minus offset)
  const endDate = new Date(today);
  endDate.setDate(today.getDate() - dateOffset);
  
  // Generate 8 days ending at endDate
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(endDate);
    date.setDate(endDate.getDate() - i);
    dates.push(date);
  }
  
  return dates;
}

function updateNavigationButtons() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  const nextBtn = document.getElementById('dateNext');
  const prevBtn = document.getElementById('datePrev');
  
  // Disable next button if we're already at today
  if (nextBtn) {
    if (dateOffset === 0) {
      nextBtn.disabled = true;
      nextBtn.style.opacity = '0.3';
      nextBtn.style.cursor = 'not-allowed';
    } else {
      nextBtn.disabled = false;
      nextBtn.style.opacity = '1';
      nextBtn.style.cursor = 'pointer';
    }
  }
  
  // Disable prev button if we've reached 30 days back
  if (prevBtn) {
    if (dateOffset >= 30) {
      prevBtn.disabled = true;
      prevBtn.style.opacity = '0.3';
      prevBtn.style.cursor = 'not-allowed';
    } else {
      prevBtn.disabled = false;
      prevBtn.style.opacity = '1';
      prevBtn.style.cursor = 'pointer';
    }
  }
}

function formatDay(date) {
  return date.toLocaleDateString('en-US', { weekday: 'short' });
}

function isSameDay(date1, date2) {
  return date1.toDateString() === date2.toDateString();
}

function updateDateSelector() {
  document.querySelectorAll('.date-card').forEach(card => {
    const cardDate = new Date(card.dataset.date);
    card.classList.toggle('selected', isSameDay(cardDate, selectedDate));
  });
}

function updateTodayLabel() {
  const label = document.getElementById('todayLabel');
  const isToday = isSameDay(selectedDate, new Date());
  
  if (isToday) {
    label.textContent = `Today, ${selectedDate.toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric' })}`;
  } else {
    label.textContent = selectedDate.toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric' });
  }
}

// Date Navigation - One day at a time with smooth transition
document.getElementById('datePrev')?.addEventListener('click', () => {
  // Only allow if we haven't reached 30 days back
  if (dateOffset < 30) {
    dateOffset += 1; // Move back 1 day
    initializeDateSelector();
  }
});

document.getElementById('dateNext')?.addEventListener('click', () => {
  // Only allow forward if we're not already at today
  if (dateOffset > 0) {
    dateOffset -= 1; // Move forward 1 day
    initializeDateSelector();
  }
});

// Load Dashboard Data
async function loadDashboardData(options = {}) {
  const { showLoading = false } = options;
  const requestId = dashboardRequestId + 1;
  dashboardRequestId = requestId;

  if (dashboardRequestController) {
    dashboardRequestController.abort();
  }

  dashboardRequestController = new AbortController();

  try {
    if (showLoading || !dashboardData) {
      setDashboardLoadingState();
    }

    const response = await fetch(getDashboardOverviewUrl(), {
      signal: dashboardRequestController.signal,
    });
    if (!response.ok) throw new Error('Failed to load dashboard');
    
    const nextDashboardData = await response.json();
    if (requestId !== dashboardRequestId) return;

    dashboardData = nextDashboardData;
    updateDashboard(dashboardData);
  } catch (error) {
    if (error.name === 'AbortError') return;
    if (requestId !== dashboardRequestId) return;

    console.error('Error loading dashboard:', error);
    setDashboardErrorState();
    showError('Could not load dashboard data');
  }
}

function getDashboardOverviewUrl() {
  const params = new URLSearchParams({
    user_id: String(getDashboardUserId()),
    date: formatApiDate(selectedDate),
  });

  return `${API_BASE}/dashboard/overview?${params.toString()}`;
}

function getDashboardUserId() {
  const pageUserId = Number(document.body?.dataset?.userId);
  if (pageUserId) {
    return pageUserId;
  }

  if (window.AGENTMOOD_USER_ID) {
    return window.AGENTMOOD_USER_ID;
  }

  try {
    if (typeof USER_ID !== 'undefined') {
      return USER_ID;
    }
  } catch (error) {
    console.warn('USER_ID is not available yet, using default user id.', error);
  }

  return 1;
}

function formatApiDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function setTextById(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function setDashboardLoadingState() {
  setTextById('stepsValue', '--');
  setTextById('activeMinutesValue', '--');
  setTextById('ringCenterValue', '--');
  resetActivityRings();
  resetCalorieBalance('Loading calorie balance...');
  setTextById('snapshotDateRange', '--');
  setTextById('snapshotPoints', '0 pts');
  setTextById('weeklyMoodLogs', '0');
  setTextById('weeklyActivitySessions', '0');
  setTextById('weeklyExerciseMinutes', '0');
  setTextById('weeklyChallenges', '0');
}

function setDashboardErrorState() {
  setTextById('stepsValue', '--');
  setTextById('activeMinutesValue', '--');
  setTextById('ringCenterValue', '--');
  resetActivityRings();
  resetCalorieBalance('Dashboard data is unavailable. Please try again.');
  setTextById('snapshotDateRange', '--');
  setTextById('snapshotPoints', '0 pts');
  setTextById('weeklyMoodLogs', '0');
  setTextById('weeklyActivitySessions', '0');
  setTextById('weeklyExerciseMinutes', '0');
  setTextById('weeklyChallenges', '0');
  renderWellnessBoardError();
  renderFallbackSuggestion(
    document.getElementById('suggestionsCarouselTrack'),
    document.getElementById('suggestionsIndicators'),
    'Dashboard suggestions are unavailable.',
  );
  initSuggestionsCarousel();
  initializeSuggestionCards();
}

function resetActivityRings() {
  const stepsRing = document.getElementById('stepsRing');
  const activeRing = document.getElementById('activeRing');
  if (stepsRing) {
    stepsRing.style.strokeDashoffset = 2 * Math.PI * 35;
  }
  if (activeRing) {
    activeRing.style.strokeDashoffset = 2 * Math.PI * 22;
  }
}

function updateDashboard(data) {
  console.log('=== UPDATE DASHBOARD CALLED ===');
  console.log('Dashboard data received:', data);
  
  // Store data globally for modal access
  window.dashboardData = data;
  window.dashboardActivityData = data.today_logs || [];
  console.log('Stored activity data for modals:', window.dashboardActivityData);
  
  // Update stats
  const stats = data.daily_stats || [];
  
  // Extract steps and calories from calorie_balance (primary source) or stats (fallback)
  let steps = 0;
  let calories = 0;
  let activeMinutes = 0;
  
  // Priority 1: Get from calorie_balance
  if (data.calorie_balance) {
    steps = data.calorie_balance.total_steps || 0;
    calories = data.calorie_balance.active_calories || 0;
    console.log('✅ Got from calorie_balance:', { steps, calories });
  } else {
    console.log('❌ No calorie_balance in data');
  }
  
  // Priority 2: Parse from stats (fallback)
  stats.forEach(stat => {
    const label = stat.label.toLowerCase();
    const value = stat.value;
    
    if (label.includes('step') && steps === 0) {
      // Parse "5,000" or "5000" format
      steps = parseInt(value.toString().replace(/,/g, '')) || 0;
      console.log('Got steps from stats:', steps);
    } else if (label.includes('calorie') && calories === 0) {
      // Parse "350 cal" format
      calories = parseInt(value.toString().replace(/[^\d]/g, '')) || 0;
      console.log('Got calories from stats:', calories);
    } else if (label.includes('exercise')) {
      // Parse "2.5 h" format to minutes
      const hours = parseFloat(value);
      if (!isNaN(hours)) {
        activeMinutes = Math.round(hours * 60);
        console.log('Got activeMinutes from stats:', activeMinutes);
      }
    }
  });
  
  console.log('Final extracted fitness data:', { steps, calories, activeMinutes });
  
  console.log('Calling updateActivitySummary with:', steps, activeMinutes);
  updateActivitySummary(steps, activeMinutes);
  
  console.log('Calling updateCalorieBalance');
  updateCalorieBalance(data.calorie_balance);
  
  console.log('Calling updatePoints');
  updatePoints(data);
  
  console.log('Calling updateWellnessBoard');
  updateWellnessBoard(data);
  
  console.log('Calling updateWeeklySuggestions');
  updateWeeklySuggestions(data);
  
  console.log('=== UPDATE DASHBOARD COMPLETE ===');
}

function updateCalorieBalance(calorieData) {
  if (!calorieData) {
    console.log('No calorie balance data available');
    resetCalorieBalance('Calorie balance is unavailable right now.');
    return;
  }
  
  console.log('Updating calorie balance:', calorieData);
  
  // Update target
  const target = calorieData.target || 0;
  document.getElementById('calorieTarget').textContent = `${target} kcal`;
  
  // Update breakdown values
  document.getElementById('mealsCalories').textContent = calorieData.meals || 0;
  document.getElementById('restingCalories').textContent = calorieData.resting_bmr || 0;
  document.getElementById('activeCalories').textContent = calorieData.active_calories || 0;
  document.getElementById('balanceCalories').textContent = calorieData.balance || 0;
  
  // Update status message - make it clearer and actionable
  const statusElement = document.querySelector('.calorie-status');
  const balance = calorieData.balance || 0;
  const meals = calorieData.meals || 0;
  
  if (meals === 0) {
    // No meals logged yet - encourage logging
    statusElement.textContent = `Log your meals to track your calorie balance! Target: ${target} kcal`;
    statusElement.style.color = '#8B7FD8'; // Purple
  } else if (balance < -500) {
    // Significant deficit
    statusElement.textContent = `You need ${Math.abs(balance)} more calories today`;
    statusElement.style.color = '#FF9F40'; // Orange
  } else if (balance < 0) {
    // Small deficit
    statusElement.textContent = `Almost there! ${Math.abs(balance)} calories to go`;
    statusElement.style.color = '#4ECDC4'; // Green
  } else if (balance > 500) {
    // Surplus
    statusElement.textContent = `You're over by ${balance} calories`;
    statusElement.style.color = '#FF6B7A'; // Red
  } else {
    // Perfect balance
    statusElement.textContent = 'Perfect balance! You hit your calorie target! 🎯';
    statusElement.style.color = '#4ECDC4'; // Green
  }
}

function resetCalorieBalance(statusMessage) {
  setTextById('calorieTarget', '-- kcal');
  setTextById('mealsCalories', '--');
  setTextById('restingCalories', '--');
  setTextById('activeCalories', '--');
  setTextById('balanceCalories', '--');

  const statusElement = document.querySelector('.calorie-status');
  if (statusElement) {
    statusElement.textContent = statusMessage;
    statusElement.style.color = '#8B7FD8';
  }
}

function updateActivitySummary(steps, activeMinutes) {
  console.log('>>> updateActivitySummary called with:', { steps, activeMinutes });
  
  // Update values
  const stepsElement = document.getElementById('stepsValue');
  const activeMinutesElement = document.getElementById('activeMinutesValue');
  const ringCenterElement = document.getElementById('ringCenterValue');
  
  if (stepsElement) {
    stepsElement.textContent = steps.toLocaleString();
    console.log('✅ Set stepsValue to:', stepsElement.textContent);
  } else {
    console.log('❌ stepsValue element not found!');
  }
  
  if (activeMinutesElement) {
    activeMinutesElement.textContent = activeMinutes;
    console.log('✅ Set activeMinutesValue to:', activeMinutesElement.textContent);
  } else {
    console.log('❌ activeMinutesValue element not found!');
  }
  
  if (ringCenterElement) {
    ringCenterElement.textContent = activeMinutes;
    console.log('✅ Set ringCenterValue to:', ringCenterElement.textContent);
  } else {
    console.log('❌ ringCenterValue element not found!');
  }
  
  // Update progress rings with concentric circles
  const stepsTarget = 10000;
  const activeTarget = 32;
  
  const stepsProgress = Math.min((steps / stepsTarget) * 100, 100);
  const activeProgress = Math.min((activeMinutes / activeTarget) * 100, 100);
  
  console.log('Progress calculated:', { stepsProgress, activeProgress });
  
  // Outer circle (steps) - radius 35 (adjusted for 90x90 SVG)
  const outerCircumference = 2 * Math.PI * 35;
  const stepsOffset = outerCircumference - (stepsProgress / 100) * outerCircumference;
  
  // Inner circle (active minutes) - radius 22 (adjusted for 90x90 SVG)
  const innerCircumference = 2 * Math.PI * 22;
  const activeOffset = innerCircumference - (activeProgress / 100) * innerCircumference;
  
  const stepsRing = document.getElementById('stepsRing');
  const activeRing = document.getElementById('activeRing');
  
  if (stepsRing) {
    stepsRing.style.strokeDashoffset = stepsOffset;
    console.log('✅ Set stepsRing offset to:', stepsOffset);
  } else {
    console.log('❌ stepsRing element not found!');
  }
  
  if (activeRing) {
    activeRing.style.strokeDashoffset = activeOffset;
    console.log('✅ Set activeRing offset to:', activeOffset);
  } else {
    console.log('❌ activeRing element not found!');
  }
  
  console.log('<<< updateActivitySummary complete');
}

function updateDistanceCard(data) {
  // Calculate distances from activities
  const activities = data.today_logs || [];
  let totalDistance = 0;
  let runningDistance = 0;
  let cyclingDistance = 0;
  
  activities.forEach(activity => {
    const detail = activity.detail.toLowerCase();
    const distance = parseFloat(activity.detail.match(/[\d.]+/)?.[0] || 0);
    
    if (detail.includes('run')) {
      runningDistance += distance;
    } else if (detail.includes('cycl') || detail.includes('bike')) {
      cyclingDistance += distance;
    }
    totalDistance += distance;
  });
  
  // Estimate moved distance from steps
  const steps = parseInt(document.getElementById('stepsValue').textContent.replace(/,/g, '')) || 0;
  const movedDistance = (steps * 0.000762).toFixed(2); // Average step length
  
  document.getElementById('movedDistance').textContent = `${movedDistance} km`;
  document.getElementById('runningDistance').textContent = `${runningDistance.toFixed(2)} km`;
  document.getElementById('cyclingDistance').textContent = `${cyclingDistance.toFixed(2)} km`;
}

function updatePoints(data) {
  const weekly = data.weekly_snapshot || {};
  const points = weekly.total_points || 0;
  document.getElementById('userPoints').textContent = points;
}

// Event Listeners
function setupEventListeners() {
  // Log Activity Button - handled by chat.js
  
  // View Insights
  document.getElementById('viewInsights')?.addEventListener('click', (e) => {
    e.preventDefault();
    if (typeof toggleChat === 'function') {
      toggleChat();
      setTimeout(() => {
        if (typeof sendMessage === 'function') {
          sendMessage('Show me my weekly insights');
        }
      }, 300);
    }
  });
  
  // Chat is handled by chat.js
}

// Auto Refresh
function startAutoRefresh() {
  // Refresh dashboard every 2 minutes
  setInterval(() => loadDashboardData({ showLoading: false }), 120000);
}

// Error Handling
function showError(message) {
  console.error(message);
  // Could add a toast notification here
}

// Utility Functions
function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  });
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatDistance(meters) {
  const km = meters / 1000;
  return `${km.toFixed(2)} km`;
}

function formatDuration(minutes) {
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins}m`;
}

// Export for debugging
window.dashboardDebug = {
  loadData: loadDashboardData,
  getData: () => dashboardData
};

// Update Wellness Board
function updateWellnessBoard(data) {
  const stats = data.daily_stats || [];
  
  // Clear existing stats
  const grid = document.getElementById('wellnessStatsGrid');
  if (!grid) return;
  grid.innerHTML = '';

  if (stats.length === 0) {
    grid.innerHTML = `
      <div class="wellness-stat-card">
        <div class="wellness-stat-icon">+</div>
        <div class="wellness-stat-label">No logs yet</div>
        <div class="wellness-stat-value">--</div>
        <div class="wellness-stat-subtitle">Use chat to start logging today.</div>
      </div>
    `;
    setTextById('wellnessStatus', 'Waiting for logs');
    return;
  }
  
  // Map stat labels to icons
  const iconMap = {
    'mood': '😊',
    'water': '💧',
    'sleep': '😴',
    'exercise': '🏃'
  };
  
  // Render each stat as a card
  stats.forEach(stat => {
    const label = stat.label.toLowerCase();
    let icon = '✓';
    let dataType = 'activity';
    
    // Determine icon and data type
    if (label.includes('mood')) {
      icon = iconMap.mood;
      dataType = 'mood';
    } else if (label.includes('water')) {
      icon = iconMap.water;
      dataType = 'water';
    } else if (label.includes('sleep')) {
      icon = iconMap.sleep;
      dataType = 'sleep';
    } else if (label.includes('exercise')) {
      icon = iconMap.exercise;
      dataType = 'exercise';
    }
    
    // Create stat card
    const card = document.createElement('div');
    card.className = 'wellness-stat-card clickable';
    card.setAttribute('data-type', dataType);
    card.onclick = () => showActivityDetails(dataType);
    
    card.innerHTML = `
      <div class="wellness-stat-icon">${icon}</div>
      <div class="wellness-stat-label">${stat.label}</div>
      <div class="wellness-stat-value">${stat.value}</div>
      <div class="wellness-stat-subtitle">${stat.detail || ''}</div>
    `;
    
    grid.appendChild(card);
  });
  
  // Update status timestamp
  const now = new Date();
  const timeStr = now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  document.getElementById('wellnessStatus').textContent = `Updated at ${timeStr}`;
}

function renderWellnessBoardError() {
  const grid = document.getElementById('wellnessStatsGrid');
  if (!grid) return;

  grid.innerHTML = `
    <div class="wellness-stat-card">
      <div class="wellness-stat-icon">!</div>
      <div class="wellness-stat-label">Dashboard unavailable</div>
      <div class="wellness-stat-value">--</div>
      <div class="wellness-stat-subtitle">Could not load wellness logs.</div>
    </div>
  `;
  setTextById('wellnessStatus', 'Could not update');
}

// Utility function to format timestamp in user's local timezone
function formatLocalTimestamp(isoString) {
  try {
    // Parse the ISO string - JavaScript automatically handles timezone conversion
    const date = new Date(isoString);
    
    // Check if date is valid
    if (isNaN(date.getTime())) {
      return 'Invalid date';
    }
    
    // Format time in local timezone
    const timeStr = date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true
    });
    
    // Format date in local timezone
    const dateStr = date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    });
    
    return `${dateStr} at ${timeStr}`;
  } catch (error) {
    console.error('Error formatting timestamp:', error, isoString);
    return 'Invalid date';
  }
}

// Detect user's timezone and send to backend
async function detectAndSetUserTimezone() {
  try {
    // Get user's timezone using Intl API
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    console.log('Detected timezone:', timezone);
    
    // Send timezone to backend
    const response = await fetch(`${API_BASE}/profile/timezone?user_id=${getDashboardUserId()}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ timezone: timezone }),
    });
    
    if (response.ok) {
      console.log('Timezone updated successfully');
    } else {
      console.warn('Failed to update timezone');
    }
  } catch (error) {
    console.error('Error detecting/setting timezone:', error);
  }
}

// Show Activity Details Modal
window.showActivityDetails = function(activityType) {
  const modal = document.getElementById('activityModal');
  const modalTitle = document.getElementById('modalTitle');
  const modalBody = document.getElementById('modalBody');
  
  // Get activity data
  let allLogs = window.dashboardActivityData || [];
  
  console.log('showActivityDetails called with type:', activityType);
  console.log('Available logs:', allLogs);
  console.log('Dashboard data:', window.dashboardData);
  
  // If no logs in window.dashboardActivityData, try to get from dashboardData
  if (allLogs.length === 0 && window.dashboardData && window.dashboardData.today_logs) {
    allLogs = window.dashboardData.today_logs;
    window.dashboardActivityData = allLogs;
    console.log('Loaded logs from dashboardData:', allLogs);
  }
  
  // Filter logs by type
  const filteredLogs = allLogs.filter(log => {
    const itemType = (log.item_type || '').toLowerCase();
    const title = (log.title || '').toLowerCase();
    const activityLower = activityType.toLowerCase();
    
    if (activityLower === 'mood') {
      return itemType === 'mood';
    } else if (activityLower === 'water') {
      return title.includes('water') || title.includes('hydration');
    } else if (activityLower === 'sleep') {
      return title.includes('sleep');
    } else if (activityLower === 'exercise') {
      return itemType === 'exercise' || title.includes('exercise') || title.includes('workout');
    }
    return false;
  });
  
  console.log('Filtered logs:', filteredLogs);
  
  // Set modal title
  const titles = {
    mood: '😊 Mood Check-ins',
    water: '💧 Water Intake',
    sleep: '😴 Sleep Logs',
    exercise: '🏃 Exercise Sessions'
  };
  modalTitle.textContent = titles[activityType] || 'Activity Details';
  
  // Build modal content
  if (filteredLogs.length === 0) {
    modalBody.innerHTML = `
      <div class="modal-empty">
        <div class="modal-empty-icon">📋</div>
        <p>No ${activityType} entries logged today yet. Use the chat to log your ${activityType}!</p>
      </div>
    `;
  } else {
    // Sort by timestamp (newest first)
    const sortedLogs = [...filteredLogs].sort((a, b) => {
      return new Date(b.created_at) - new Date(a.created_at);
    });
    
    const logsHTML = sortedLogs.map(log => {
      const title = log.title || '';
      const detail = log.detail || '';
      const timestamp = formatLocalTimestamp(log.created_at);
      
      return `
        <div class="activity-detail-item">
          <div class="activity-detail-time">${timestamp}</div>
          <div class="activity-detail-value">${escapeHtml(title)}</div>
          ${detail ? `<div class="activity-detail-note">${escapeHtml(detail)}</div>` : ''}
        </div>
      `;
    }).join('');
    
    modalBody.innerHTML = logsHTML;
  }
  
  // Show modal
  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
};

// Close Activity Details Modal
window.closeActivityModal = function() {
  const modal = document.getElementById('activityModal');
  modal.classList.remove('active');
  document.body.style.overflow = '';
};

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeActivityModal();
  }
});

// Update Weekly Suggestions
function updateWeeklySuggestions(data) {
  const weekly = data.weekly_snapshot || {};
  const suggestions = data.suggestions || [];
  
  // Update snapshot card - use correct field names from backend
  const startDate = weekly.week_start || weekly.start_date;
  const endDate = weekly.week_end || weekly.end_date;
  const points = weekly.total_points || 0;
  
  document.getElementById('snapshotDateRange').textContent = 
    startDate && endDate ? `${formatDateShort(startDate)} TO ${formatDateShort(endDate)}` : '--';
  document.getElementById('snapshotPoints').textContent = `⭐ ${points} pts`;
  
  // Update snapshot stats
  document.getElementById('weeklyMoodLogs').textContent = weekly.mood_logs || 0;
  document.getElementById('weeklyActivitySessions').textContent = weekly.activity_sessions || 0;
  document.getElementById('weeklyExerciseMinutes').textContent = weekly.exercise_minutes || 0;
  document.getElementById('weeklyChallenges').textContent = weekly.completed_challenges || 0;
  
  // Update suggestions carousel
  const carouselTrack = document.getElementById('suggestionsCarouselTrack');
  const indicatorsContainer = document.getElementById('suggestionsIndicators');
  
  if (!carouselTrack || !indicatorsContainer) {
    console.warn('Suggestions carousel containers not found');
    return;
  }
  
  if (suggestions.length === 0) {
    renderFallbackSuggestion(carouselTrack, indicatorsContainer);
    initSuggestionsCarousel();
    initializeSuggestionCards();
    return;
  }
  
  // Build suggestions HTML
  const suggestionsHTML = suggestions.map(suggestion => {
    const category = suggestion.category_label || 'Exercise';
    const contentType = suggestion.content_type || 'Video';
    const title = suggestion.title || 'Wellness Activity';
    const duration = suggestion.duration || '15 min';
    const contentId = suggestion.content_id || '';
    const url = suggestion.url || '';
    const reason = suggestion.reason || 'Recommended for you';
    
    // Determine icon based on category
    let iconEmoji = '🏃';
    if (category.toLowerCase().includes('mindfulness') || category.toLowerCase().includes('meditation')) {
      iconEmoji = '🧘';
    } else if (category.toLowerCase().includes('nutrition') || category.toLowerCase().includes('food')) {
      iconEmoji = '🥗';
    } else if (category.toLowerCase().includes('sleep')) {
      iconEmoji = '😴';
    } else if (category.toLowerCase().includes('water') || category.toLowerCase().includes('hydration')) {
      iconEmoji = '💧';
    }
    
    // Determine content type icon
    const typeIcon = contentType.toLowerCase().includes('video') ? '🎥' : '📄';
    
    return `
      <div class="featured-suggestion">
        <div class="suggestion-icon-wrapper">${iconEmoji}</div>
        <div class="suggestion-content-wrapper">
          <div class="suggestion-meta-row">
            <div class="suggestion-badge">${escapeHtml(category)}</div>
            <div class="suggestion-icon">${typeIcon} ${escapeHtml(contentType)}</div>
          </div>
          <h4 class="suggestion-title-compact">${escapeHtml(title)}</h4>
          <div class="suggestion-reason">${escapeHtml(reason)}</div>
          <div class="suggestion-duration">${escapeHtml(duration)}</div>
        </div>
        <button class="suggestion-btn-compact" data-content-id="${contentId}" data-content-type="${contentType}" data-url="${escapeHtml(url)}">Start Now -&gt;</button>
      </div>
    `;
  }).join('');
  
  carouselTrack.innerHTML = suggestionsHTML;
  
  // Create indicators
  const indicatorsHTML = suggestions.map((_, index) => 
    `<button class="suggestions-indicator ${index === 0 ? 'active' : ''}" data-index="${index}" aria-label="Go to suggestion ${index + 1}"></button>`
  ).join('');
  indicatorsContainer.innerHTML = indicatorsHTML;
  
  // Initialize carousel
  initSuggestionsCarousel();
  
  // Re-initialize click handlers for newly added suggestions
  initializeSuggestionCards();
}

function renderFallbackSuggestion(carouselTrack, indicatorsContainer, reasonText = 'Suggestions will update after more activity is logged.') {
  if (!carouselTrack || !indicatorsContainer) return;

  carouselTrack.innerHTML = `
    <div class="featured-suggestion">
      <div class="suggestion-icon-wrapper">+</div>
      <div class="suggestion-content-wrapper">
        <div class="suggestion-meta-row">
          <div class="suggestion-badge">Wellness</div>
          <div class="suggestion-icon">Chat</div>
        </div>
        <h4 class="suggestion-title-compact">Keep logging your day</h4>
        <div class="suggestion-reason">${escapeHtml(reasonText)}</div>
        <div class="suggestion-duration">Anytime</div>
      </div>
      <button class="suggestion-btn-compact" data-content-id="" data-content-type="chat" data-url="">Open Chat</button>
    </div>
  `;

  indicatorsContainer.innerHTML = `
    <button class="suggestions-indicator active" data-index="0" aria-label="Go to suggestion 1"></button>
  `;
}

// Suggestions Carousel Logic
let currentSuggestionIndex = 0;
let totalSuggestions = 0;

function initSuggestionsCarousel() {
  const track = document.getElementById('suggestionsCarouselTrack');
  const prevBtn = document.getElementById('suggestionsPrev');
  const nextBtn = document.getElementById('suggestionsNext');
  const indicators = document.querySelectorAll('.suggestions-indicator');
  
  if (!track || !prevBtn || !nextBtn) return;
  
  totalSuggestions = track.children.length;
  currentSuggestionIndex = 0;
  
  // Button handlers are assigned instead of stacked on every refresh.
  prevBtn.onclick = () => navigateSuggestion(-1);
  nextBtn.onclick = () => navigateSuggestion(1);
  
  // Indicator handlers
  indicators.forEach((indicator, index) => {
    indicator.onclick = () => goToSuggestion(index);
  });
  
  updateSuggestionsCarousel();
}

function navigateSuggestion(direction) {
  currentSuggestionIndex += direction;
  
  if (currentSuggestionIndex < 0) {
    currentSuggestionIndex = totalSuggestions - 1;
  } else if (currentSuggestionIndex >= totalSuggestions) {
    currentSuggestionIndex = 0;
  }
  
  updateSuggestionsCarousel();
}

function goToSuggestion(index) {
  currentSuggestionIndex = index;
  updateSuggestionsCarousel();
}

function updateSuggestionsCarousel() {
  const track = document.getElementById('suggestionsCarouselTrack');
  const prevBtn = document.getElementById('suggestionsPrev');
  const nextBtn = document.getElementById('suggestionsNext');
  const indicators = document.querySelectorAll('.suggestions-indicator');
  
  if (!track) return;
  
  // Update track position
  const offset = -currentSuggestionIndex * 100;
  track.style.transform = `translateX(${offset}%)`;
  
  // Update button states
  if (prevBtn && nextBtn) {
    prevBtn.disabled = totalSuggestions <= 1;
    nextBtn.disabled = totalSuggestions <= 1;
  }
  
  // Update indicators
  indicators.forEach((indicator, index) => {
    indicator.classList.toggle('active', index === currentSuggestionIndex);
  });
}

// Open suggestion content
window.openSuggestion = function(contentId) {
  if (!contentId) {
    if (typeof toggleChat === 'function') {
      toggleChat();
    }
    return;
  }
  
  // Open chat and ask about the content
  if (typeof toggleChat === 'function' && typeof sendMessage === 'function') {
    toggleChat();
    setTimeout(() => {
      sendMessage(`Tell me more about content ${contentId}`);
    }, 300);
  }
};
// Format date for snapshot
function formatDateShort(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  });
}


// Open suggestion content
function openSuggestion(contentId, contentType) {
  if (!contentId) {
    if (typeof toggleChat === 'function') {
      toggleChat();
    } else {
      openChat();
    }
    return;
  }
  
  // If it's a video, open in a modal or new window
  if (contentType && contentType.toLowerCase().includes('video')) {
    // Open video in a modal or player
    openVideoContent(contentId);
  } else {
    // Open article/content
    openArticleContent(contentId);
  }
}

// Open chat widget
function openChat() {
  const chatToggleBtn = document.getElementById('chatToggleBtn');
  const chatWidget = document.getElementById('chatWidget');
  
  if (chatToggleBtn && chatWidget) {
    chatToggleBtn.classList.add('active');
    chatWidget.classList.add('active');
  }
}

// Open video content
function openVideoContent(contentId) {
  // Create a modal for video
  const modal = document.createElement('div');
  modal.className = 'content-modal';
  modal.innerHTML = `
    <div class="content-modal-overlay" onclick="this.parentElement.remove()">
      <div class="content-modal-container" onclick="event.stopPropagation()">
        <button class="content-modal-close" onclick="this.closest('.content-modal').remove()">✕</button>
        <div class="video-player">
          <iframe width="100%" height="600" src="https://www.youtube.com/embed/${contentId}" frameborder="0" allowfullscreen></iframe>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
}

// Open article content
function openArticleContent(contentId) {
  // Open article in a new tab or modal
  window.open(`/article/${contentId}`, '_blank');
}

// Close chat widget
function closeChat() {
  const chatToggleBtn = document.getElementById('chatToggleBtn');
  const chatWidget = document.getElementById('chatWidget');
  
  if (chatToggleBtn && chatWidget) {
    chatToggleBtn.classList.remove('active');
    chatWidget.classList.remove('active');
  }
}

// Initialize suggestion card click handlers
function initializeSuggestionCards() {
  // Add click handlers to all suggestion buttons
  const buttons = document.querySelectorAll('.suggestion-btn-compact');
  buttons.forEach(button => {
    button.onclick = function(e) {
      e.stopPropagation();
      e.preventDefault();
      const contentId = this.getAttribute('data-content-id');
      const contentType = this.getAttribute('data-content-type');
      const url = this.getAttribute('data-url');
      console.log('Button clicked!', contentId, contentType, url);
      
      // Open the actual content URL
      if (url) {
        window.open(url, '_blank');
      } else {
        // Fallback to openSuggestion if no URL
        openSuggestion(contentId, contentType);
      }
    };
  });
}

// initializeSuggestionCards is called from the main DOMContentLoaded handler above
