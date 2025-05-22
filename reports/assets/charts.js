/**
 * Android Performance Report - Chart Functions
 */

/**
 * Initialize CPU usage chart
 * @param {string} elementId - Canvas element ID
 * @param {Array} data - CPU usage data points
 */
function initCpuChart(elementId, data) {
  const ctx = document.getElementById(elementId).getContext('2d');
  
  // Extract timestamps and CPU values
  const timestamps = data.map(point => point.timestamp);
  const cpuValues = data.map(point => point.value);
  
  // Format timestamps for display
  const labels = timestamps.map(timestamp => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { minute: '2-digit', second: '2-digit' });
  });
  
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'CPU Usage (%)',
        data: cpuValues,
        borderColor: '#4285f4',
        backgroundColor: 'rgba(66, 133, 244, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.2,
        pointRadius: 3,
        pointBackgroundColor: '#4285f4'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            label: function(context) {
              return `CPU: ${context.parsed.y.toFixed(1)}%`;
            }
          }
        }
      },
      scales: {
        x: {
          grid: {
            display: false
          },
          ticks: {
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 6
          }
        },
        y: {
          beginAtZero: true,
          suggestedMax: 100,
          ticks: {
            callback: function(value) {
              return value + '%';
            }
          }
        }
      }
    }
  });
}

/**
 * Initialize startup time chart
 * @param {string} elementId - Canvas element ID
 * @param {Array} data - Startup time measurements
 */
function initStartupChart(elementId, data) {
  const ctx = document.getElementById(elementId).getContext('2d');
  
  // Extract measurement values
  const measurements = data.map((item, index) => ({
    index: index + 1,
    total: item.total_time_ms,
    wait: item.wait_time_ms
  }));
  
  const labels = measurements.map(m => `Run ${m.index}`);
  const totalTimes = measurements.map(m => m.total);
  const waitTimes = measurements.map(m => m.wait);
  
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Total Time (ms)',
          data: totalTimes,
          backgroundColor: 'rgba(66, 133, 244, 0.7)',
          borderColor: '#4285f4',
          borderWidth: 1
        },
        {
          label: 'Wait Time (ms)',
          data: waitTimes,
          backgroundColor: 'rgba(251, 188, 5, 0.7)',
          borderColor: '#fbbc05',
          borderWidth: 1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top'
        },
        tooltip: {
          mode: 'index',
          intersect: false
        }
      },
      scales: {
        x: {
          grid: {
            display: false
          }
        },
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: 'Time (ms)'
          }
        }
      }
    }
  });
}

/**
 * Initialize memory breakdown chart
 * @param {string} elementId - Canvas element ID
 * @param {Object} data - Memory breakdown data
 */
function initMemoryChart(elementId, data) {
  const ctx = document.getElementById(elementId).getContext('2d');
  
  // Extract memory values
  const memoryData = [
    data.native_heap_mb || 0,
    data.dalvik_heap_mb || 0,
    data.graphics_mb || 0,
    (data.total_pss_mb || 0) - 
      ((data.native_heap_mb || 0) + 
       (data.dalvik_heap_mb || 0) + 
       (data.graphics_mb || 0))
  ];
  
  // Ensure "Other" is not negative
  memoryData[3] = Math.max(0, memoryData[3]);
  
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Native Heap', 'Dalvik Heap', 'Graphics', 'Other'],
      datasets: [{
        data: memoryData,
        backgroundColor: [
          '#4285f4',
          '#34a853',
          '#fbbc05',
          '#ea4335'
        ],
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: {
            boxWidth: 15
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const value = context.parsed;
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percentage = Math.round((value / total) * 100);
              return `${context.label}: ${value.toFixed(1)} MB (${percentage}%)`;
            }
          }
        }
      }
    }
  });
}

/**
 * Initialize frame metrics chart
 * @param {string} elementId - Canvas element ID
 * @param {Object} data - Frame metrics data
 */
function initFrameMetricsChart(elementId, data) {
  const ctx = document.getElementById(elementId).getContext('2d');
  
  const smoothFrames = data.total_frames - data.janky_frames;
  
  new Chart(ctx, {
    type: 'pie',
    data: {
      labels: ['Smooth Frames', 'Janky Frames'],
      datasets: [{
        data: [smoothFrames, data.janky_frames],
        backgroundColor: [
          '#34a853',
          '#ea4335'
        ],
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom'
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const value = context.parsed;
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percentage = Math.round((value / total) * 100);
              return `${context.label}: ${value} (${percentage}%)`;
            }
          }
        }
      }
    }
  });
}
