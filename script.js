(function () {
  "use strict";

  /* ---------------------------------------------------------
     Mobile nav toggle
     --------------------------------------------------------- */
  const nav = document.getElementById("nav");
  const navToggle = document.getElementById("navToggle");

  navToggle.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("menu-open");
    navToggle.classList.toggle("open", isOpen);
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });

  document.querySelectorAll(".nav-links a").forEach((link) => {
    link.addEventListener("click", () => {
      nav.classList.remove("menu-open");
      navToggle.classList.remove("open");
      navToggle.setAttribute("aria-expanded", "false");
    });
  });

  /* ---------------------------------------------------------
     Scroll reveal
     --------------------------------------------------------- */
  const revealItems = document.querySelectorAll(".reveal");

  if ("IntersectionObserver" in window && revealItems.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    revealItems.forEach((item) => observer.observe(item));
  } else {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  }

  /* ---------------------------------------------------------
     Backend config + health check
     --------------------------------------------------------- */
  const apiUrlInput = document.getElementById("apiUrl");
  const apiStatus = document.getElementById("apiStatus");
  const apiStatusText = document.getElementById("apiStatusText");

  const STORAGE_KEY = "pulse_api_url";
  const savedUrl = localStorage.getItem(STORAGE_KEY);
  if (savedUrl) apiUrlInput.value = savedUrl;

  function getApiBase() {
    return apiUrlInput.value.trim().replace(/\/+$/, "");
  }

  async function checkApiHealth() {
    const base = getApiBase();
    if (!base) return;

    apiStatus.className = "api-status";
    apiStatusText.textContent = "Checking...";

    try {
      const res = await fetch(`${base}/`, { method: "GET" });
      if (!res.ok) throw new Error("bad status");
      apiStatus.className = "api-status online";
      apiStatusText.textContent = "Connected";
    } catch (err) {
      apiStatus.className = "api-status offline";
      apiStatusText.textContent = "Unreachable";
    }
  }

  let healthTimer;
  apiUrlInput.addEventListener("input", () => {
    localStorage.setItem(STORAGE_KEY, apiUrlInput.value.trim());
    clearTimeout(healthTimer);
    healthTimer = setTimeout(checkApiHealth, 500);
  });

  checkApiHealth();

  /* ---------------------------------------------------------
     Analyze form
     --------------------------------------------------------- */
  const form = document.getElementById("analyzeForm");
  const submitBtn = document.getElementById("submitBtn");
  const submitBtnText = document.getElementById("submitBtnText");
  const formError = document.getElementById("formError");

  const resultEmpty = document.getElementById("resultEmpty");
  const resultPanel = document.getElementById("resultPanel");

  const gaugeFill = document.getElementById("gaugeFill");
  const gaugeScore = document.getElementById("gaugeScore");
  const riskBadge = document.getElementById("riskBadge");
  const factorList = document.getElementById("factorList");
  const recList = document.getElementById("recList");
  const resultSummary = document.getElementById("resultSummary");

  const GAUGE_CIRCUMFERENCE = 427.3;

  const RISK_STYLES = {
    "Healthy": { color: "#5FE3C3" },
    "Mild Concern": { color: "#FFD166" },
    "Moderate Risk": { color: "#FF9F5A" },
    "High Risk": { color: "#FF6B7A" }
  };

  function readFormPayload() {
    return {
      age: Number(document.getElementById("age").value),
      gender: document.getElementById("gender").value,
      country: document.getElementById("country").value.trim(),
      academic_level: document.getElementById("academicLevel").value,
      most_used_platform: document.getElementById("platform").value,
      purpose_of_use: document.getElementById("purpose").value,
      avg_daily_usage_hours: Number(document.getElementById("usageHours").value),
      daily_unlocks: Number(document.getElementById("unlocks").value),
      study_hours: Number(document.getElementById("studyHours").value),
      physical_activity_hours: Number(document.getElementById("activityHours").value),
      sleep_hours_per_night: Number(document.getElementById("sleepHours").value),
      stress_level: document.getElementById("stress").value
    };
  }

  function validatePayload(payload) {
    if (!payload.country) return "Country can't be empty.";
    for (const key of ["age", "avg_daily_usage_hours", "daily_unlocks", "study_hours", "physical_activity_hours", "sleep_hours_per_night"]) {
      if (Number.isNaN(payload[key])) return "Please fill in every field with a valid number.";
    }
    return null;
  }

  function setLoading(isLoading) {
    submitBtn.disabled = isLoading;
    submitBtnText.textContent = isLoading ? "Reading..." : "Read my pulse";
  }

  function renderResult(data) {
    resultEmpty.hidden = true;
    resultPanel.hidden = false;

    const score = Math.max(0, Math.min(10, data.mental_health_score));
    const offset = GAUGE_CIRCUMFERENCE - (score / 10) * GAUGE_CIRCUMFERENCE;
    const style = RISK_STYLES[data.risk_level] || { color: "#5FE3C3" };

    requestAnimationFrame(() => {
      gaugeFill.style.stroke = style.color;
      gaugeFill.style.strokeDashoffset = String(offset);
    });

    gaugeScore.textContent = score.toFixed(2);

    riskBadge.textContent = data.risk_level;
    riskBadge.style.color = style.color;
    riskBadge.style.background = hexToSoftBg(style.color);

    factorList.innerHTML = "";
    (data.top_factors || []).forEach((factor) => {
      const li = document.createElement("li");
      li.textContent = factor;
      factorList.appendChild(li);
    });

    recList.innerHTML = "";
    (data.recommendations || []).forEach((rec) => {
      const li = document.createElement("li");
      li.textContent = rec;
      recList.appendChild(li);
    });

    resultSummary.textContent = data.summary || "";
  }

  function hexToSoftBg(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, 0.14)`;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.textContent = "";

    const payload = readFormPayload();
    const validationError = validatePayload(payload);
    if (validationError) {
      formError.textContent = validationError;
      return;
    }

    const base = getApiBase();
    if (!base) {
      formError.textContent = "Set the backend URL above before running an analysis.";
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(`${base}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail && detail.detail ? detail.detail : `Request failed (${res.status})`);
      }

      const data = await res.json();
      renderResult(data);
      apiStatus.className = "api-status online";
      apiStatusText.textContent = "Connected";
    } catch (err) {
      formError.textContent =
        "Can't reach the model server. Make sure your FastAPI backend is running at " + base + ".";
      apiStatus.className = "api-status offline";
      apiStatusText.textContent = "Unreachable";
    } finally {
      setLoading(false);
    }
  });
})();
