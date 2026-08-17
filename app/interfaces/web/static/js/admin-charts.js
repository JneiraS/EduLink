const CHART_COLORS = {
  primary: "#65AFFF",
  secondary: "#6CCFF6",
  success: "#68B684",
  warning: "#FFCB47",
  danger: "#DF928E",
  muted: "#8b93a7",
};

function chartThemeColors() {
  const theme = document.documentElement.getAttribute("data-theme") || "light";
  const dark = theme === "dark";
  return {
    grid: dark ? "rgba(255,255,255,0.06)" : "rgba(20,24,42,0.06)",
    ticks: dark ? "#c3c9d9" : "#5b6378",
    legend: dark ? "#e6e9f2" : "#2a2f45",
  };
}

function readChartData(canvas) {
  const raw = canvas.dataset.chart;
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch (error) {
    console.error("Invalid chart data on", canvas.id, error);
    return null;
  }
}

function registerChart(canvasId, build) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const data = readChartData(canvas);
  if (!data) return;
  const colors = chartThemeColors();
  new Chart(canvas.getContext("2d"), build(data, colors));
}

function renderAdminCharts() {
  if (typeof Chart === "undefined") return;
  const colors = chartThemeColors();

  registerChart("chart-registrations", (data) => ({
    type: "bar",
    data: {
      labels: data.map((row) => row.label),
      datasets: [
        {
          label: "Inscriptions",
          data: data.map((row) => row.count),
          backgroundColor: hexWithAlpha(CHART_COLORS.primary),
          borderRadius: 4,
        },
      ],
    },
    options: baseOptions(colors, {
      scales: {
        y: {
          beginAtZero: true,
          ticks: { color: colors.ticks },
          grid: { color: colors.grid },
        },
        x: {
          ticks: { color: colors.ticks, maxRotation: 45, autoSkip: false },
          grid: { display: false },
        },
      },
    }),
  }));

  registerChart("chart-users-by-role", (data) => ({
    type: "doughnut",
    data: {
      labels: Object.keys(data),
      datasets: [
        {
          data: Object.values(data),
          backgroundColor: [
            CHART_COLORS.primary,
            CHART_COLORS.secondary,
            CHART_COLORS.success,
          ],
          borderWidth: 0.5,
        },
      ],
    },
    options: {
      plugins: {
        legend: { position: "bottom", labels: { color: colors.legend } },
      },
    },
  }));

  registerChart("chart-messages-by-day", (data) => ({
    type: "line",
    data: {
      labels: data.map((row) => row.label),
      datasets: [
        {
          label: "Messages",
          data: data.map((row) => row.count),
          borderColor: CHART_COLORS.secondary,
          backgroundColor: hexWithAlpha(CHART_COLORS.secondary),
          fill: true,
          tension: 0.3,
          pointRadius: 3,
        },
      ],
    },
    options: baseOptions(colors, {
      scales: {
        y: {
          beginAtZero: true,
          ticks: { color: colors.ticks },
          grid: { color: colors.grid },
        },
        x: {
          ticks: { color: colors.ticks, maxRotation: 45, autoSkip: true },
          grid: { display: false },
        },
      },
    }),
  }));

  registerChart("chart-top-channels", (data) => ({
    type: "bar",
    data: {
      labels: data.map((row) => row.channel_name),
      datasets: [
        {
          label: "Messages",
          data: data.map((row) => row.count),
          backgroundColor: hexWithAlpha(CHART_COLORS.success),
          borderRadius: 4,
        },
      ],
    },
    options: {
      indexAxis: "y",
      plugins: { legend: { display: false } },
      scales: {
        x: {
          beginAtZero: true,
          ticks: {
            color: colors.ticks,
            stepSize: 1,
            precision: 0,
          },
          grid: {
            color: colors.grid,
          },
        },
        y: {
          ticks: {
            color: colors.ticks,
          },
          grid: {
            display: false,
          },
        },
      },
    },
  }));

  registerChart("chart-read-rates", (data) => ({
    type: "bar",
    data: {
      labels: data.map((row) => row.title),
      datasets: [
        {
          label: "Lues",
          data: data.map((row) => row.read),
          backgroundColor: hexWithAlpha(CHART_COLORS.success),
          borderRadius: 4,
        },
        {
          label: "Non lues",
          data: data.map((row) => row.unread),
          backgroundColor: hexWithAlpha(CHART_COLORS.danger),
          borderRadius: 4,
        },
      ],
    },
    options: baseOptions(colors, {
      scales: {
        x: {
          stacked: true,
          ticks: { color: colors.ticks, maxRotation: 45, autoSkip: false },
          grid: { display: false },
        },
        y: {
          stacked: true,
          beginAtZero: true,
          ticks: { color: colors.ticks },
          grid: { color: colors.grid },
        },
      },
    }),
  }));

  registerChart("chart-push-adoption", (data) => ({
    type: "doughnut",
    data: {
      labels: ["Abonnes push", "Sans abonnement"],
      datasets: [
        {
          data: [
            data.subscribers,
            Math.max(data.total_users - data.subscribers, 0),
          ],
          backgroundColor: [CHART_COLORS.warning, CHART_COLORS.muted],
          borderWidth: 0.5,
        },
      ],
    },
    options: {
      plugins: {
        legend: { position: "bottom", labels: { color: colors.legend } },
      },
    },
  }));
}

function hexWithAlpha(hex) {
  return hex;
}

function baseOptions(colors, extra) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: colors.legend } },
    },
    ...extra,
  };
}

document.addEventListener("DOMContentLoaded", renderAdminCharts);
