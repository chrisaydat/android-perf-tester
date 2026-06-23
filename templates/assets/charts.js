(() => {
  const node = document.getElementById("perf-data");
  if (!node) return;
  window.androidPerfReport = JSON.parse(node.textContent || "{}");
})();
