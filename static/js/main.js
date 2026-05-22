document.addEventListener("DOMContentLoaded", () => {
  // Global State
  let currentConfig = { device: "auto" };
  let hardwareDiagnostics = { cuda_available: false, gpu_name: null, docling_available: false, torch_available: false };
  let recentExtractions = [];
  let activeExtractionId = null;

  // DOM Elements
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const historyContainer = document.getElementById("history-container");
  const historyEmpty = document.getElementById("history-empty");
  
  const viewerDocTitle = document.getElementById("viewer-doc-title");
  const viewerDocMeta = document.getElementById("viewer-doc-meta");
  const viewerActions = document.getElementById("viewer-actions");
  const markdownRenderer = document.getElementById("markdown-renderer");
  const loadingOverlay = document.getElementById("loading-overlay");
  const progressMessage = document.getElementById("progress-message");
  const progressStep = document.getElementById("progress-step");
  
  const copyBtn = document.getElementById("copy-btn");
  const downloadBtn = document.getElementById("download-btn");
  
  const openConfigBtn = document.getElementById("open-config-btn");
  const closeConfigBtn = document.getElementById("close-config-btn");
  const configModalOverlay = document.getElementById("config-modal-overlay");
  const saveConfigBtn = document.getElementById("save-config-btn");
  
  const radAuto = document.getElementById("rad-auto");
  const radCpu = document.getElementById("rad-cpu");
  const radGpu = document.getElementById("rad-gpu");
  const deviceOptions = document.querySelectorAll(".device-option");
  
  const diagTorch = document.getElementById("diag-torch");
  const diagCuda = document.getElementById("diag-cuda");
  const diagDocling = document.getElementById("diag-docling");
  const gpuDetectRow = document.getElementById("gpu-detect-row");
  const gpuDetectedName = document.getElementById("gpu-detected-name");
  
  const globalStatusDot = document.getElementById("global-status-dot");
  const globalStatusText = document.getElementById("global-status-text");
  
  const toast = document.getElementById("app-toast");
  const toastText = document.getElementById("toast-text");
  const toastIcon = document.getElementById("toast-icon");

  // Load Initial Configurations
  fetchConfig();

  // --- Modal Config Management ---
  openConfigBtn.addEventListener("click", () => {
    // Populate form selections based on current state
    setSelectedDeviceOption(currentConfig.device);
    updateDiagnosticsUI();
    configModalOverlay.classList.add("active");
  });

  closeConfigBtn.addEventListener("click", () => {
    configModalOverlay.classList.remove("active");
  });

  // Close modal when clicking on outer backdrop
  configModalOverlay.addEventListener("click", (e) => {
    if (e.target === configModalOverlay) {
      configModalOverlay.classList.remove("active");
    }
  });

  // Handle segmented hardware option clicks
  deviceOptions.forEach(opt => {
    opt.addEventListener("click", () => {
      const selectedDevice = opt.getAttribute("data-device");
      setSelectedDeviceOption(selectedDevice);
    });
  });

  function setSelectedDeviceOption(device) {
    deviceOptions.forEach(opt => {
      opt.classList.remove("selected");
      const radio = opt.querySelector("input[type='radio']");
      if (radio) radio.checked = false;
    });

    const activeOpt = document.getElementById(`opt-${device}`);
    if (activeOpt) {
      activeOpt.classList.add("selected");
      const radio = activeOpt.querySelector("input[type='radio']");
      if (radio) radio.checked = true;
    }
  }

  saveConfigBtn.addEventListener("click", async () => {
    const selectedRadio = document.querySelector("input[name='device']:checked");
    if (!selectedRadio) return;

    const deviceChoice = selectedRadio.value;
    try {
      saveConfigBtn.disabled = true;
      saveConfigBtn.innerHTML = `<span>Saving...</span>`;
      
      const response = await fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device: deviceChoice })
      });
      
      const data = await response.json();
      if (data.success) {
        currentConfig = data.config;
        hardwareDiagnostics = data.hardware_status;
        
        updateGlobalStatusIndicator();
        showToast("Settings updated successfully!", "success", "check");
        configModalOverlay.classList.remove("active");
      } else {
        showToast(data.error || "Failed to update configuration", "danger", "alert-triangle");
      }
    } catch (err) {
      showToast("Server communication error occurred", "danger", "wifi-off");
    } finally {
      saveConfigBtn.disabled = false;
      saveConfigBtn.innerHTML = `<i data-lucide="check"></i><span>Save Changes</span>`;
      lucide.createIcons();
    }
  });

  async function fetchConfig() {
    try {
      const response = await fetch("/api/config");
      const data = await response.json();
      if (data.success) {
        currentConfig = data.config;
        hardwareDiagnostics = data.hardware_status;
        
        updateGlobalStatusIndicator();
        updateDiagnosticsUI();
      }
    } catch (err) {
      console.error("Error fetching project settings:", err);
    }
  }

  function updateGlobalStatusIndicator() {
    // Reset dot classes
    globalStatusDot.className = "status-dot";
    
    const dev = currentConfig.device;
    const cuda = hardwareDiagnostics.cuda_available;

    if (dev === "gpu" || (dev === "auto" && cuda)) {
      if (cuda) {
        globalStatusDot.classList.add("active-gpu");
        globalStatusText.textContent = "GPU Enabled";
        globalStatusText.style.color = "var(--color-accent)";
      } else {
        globalStatusDot.classList.add("active-cpu");
        globalStatusText.textContent = "CPU Fallback";
        globalStatusText.style.color = "var(--color-warning)";
      }
    } else {
      globalStatusDot.classList.add("active-cpu");
      globalStatusText.textContent = "CPU Mode";
      globalStatusText.style.color = "var(--color-primary)";
    }
  }

  function updateDiagnosticsUI() {
    // Render Torch state
    if (hardwareDiagnostics.torch_available) {
      diagTorch.innerHTML = `<span class="badge-success">Loaded</span>`;
    } else {
      diagTorch.innerHTML = `<span class="badge-warning">Not Found</span>`;
    }

    // Render CUDA state
    if (hardwareDiagnostics.cuda_available) {
      diagCuda.innerHTML = `<span class="badge-success">CUDA Active</span>`;
      gpuDetectRow.style.display = "flex";
      gpuDetectedName.textContent = hardwareDiagnostics.gpu_name || "NVIDIA Graphics Device";
    } else {
      diagCuda.innerHTML = `<span class="badge-warning">Unavailable</span>`;
      gpuDetectRow.style.display = "none";
    }

    // Render Docling state
    if (hardwareDiagnostics.docling_available) {
      diagDocling.innerHTML = `<span class="badge-success">Installed</span>`;
    } else {
      diagDocling.innerHTML = `<span class="badge-info">Simulation (Lite)</span>`;
    }
    
    lucide.createIcons();
  }

  // --- File Drag & Drop Handlers ---
  ["dragenter", "dragover"].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropZone.classList.add("dragover");
    }, false);
  });

  ["dragleave", "drop"].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropZone.classList.remove("dragover");
    }, false);
  });

  dropZone.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length) handleFileSelect(files[0]);
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) handleFileSelect(fileInput.files[0]);
  });

  function handleFileSelect(file) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      showToast("Only PDF documents are supported.", "danger", "alert-circle");
      return;
    }
    uploadDocument(file);
  }

  // --- Document Upload & Async Processing ---
  async function uploadDocument(file) {
    const formData = new FormData();
    formData.append("file", file);

    try {
      // Trigger loading screen
      setViewerLoading(true, "Uploading File...", "Sending document securely to converter pipeline");
      
      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData
      });

      const data = await response.json();
      if (data.success) {
        pollStatus(data.task_id, data.filename);
      } else {
        setViewerLoading(false);
        showToast(data.error || "Failed to initiate parsing task", "danger", "alert-triangle");
      }
    } catch (err) {
      setViewerLoading(false);
      showToast("Failed to connect to the backend server", "danger", "wifi-off");
    }
  }

  function setViewerLoading(isLoading, msg = "", step = "") {
    if (isLoading) {
      progressMessage.textContent = msg;
      progressStep.textContent = step;
      loadingOverlay.classList.add("active");
      viewerActions.style.display = "none";
    } else {
      loadingOverlay.classList.remove("active");
    }
  }

  function pollStatus(taskId, filename) {
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      try {
        const response = await fetch(`/api/status/${taskId}`);
        const data = await response.json();

        if (data.success) {
          const task = data.task;
          
          if (task.status === "processing") {
            progressMessage.textContent = task.message || "Running Docling parsing...";
            progressStep.textContent = `Completed steps... ${task.progress}%`;
          } 
          else if (task.status === "completed") {
            clearInterval(interval);
            setViewerLoading(false);
            
            // Add to session store
            const newExtraction = {
              id: taskId,
              filename: filename,
              text: task.result.text,
              device: task.result.device_used,
              warning: task.result.warning,
              timestamp: new Date().toLocaleTimeString()
            };
            
            recentExtractions.unshift(newExtraction);
            activeExtractionId = taskId;
            
            updateHistoryUI();
            renderDocument(newExtraction);
            showToast("Document layout extracted successfully!", "success", "check-circle");
          } 
          else if (task.status === "failed") {
            clearInterval(interval);
            setViewerLoading(false);
            showToast(task.error || "Parser task failed.", "danger", "alert-triangle");
            renderErrorState(task.error || "Unknown extraction pipeline failure.");
          }
        } else {
          clearInterval(interval);
          setViewerLoading(false);
          showToast("Task tracking session lost.", "danger", "alert-octagon");
        }
      } catch (err) {
        // Tolerates brief connection drops, stops after 5 consecutive failures
        if (attempts > 50) {
          clearInterval(interval);
          setViewerLoading(false);
          showToast("Failed to contact task monitor.", "danger", "wifi-off");
        }
      }
    }, 1000);
  }

  // --- Render Layout Data in Viewer ---
  function renderDocument(doc) {
    viewerDocTitle.textContent = doc.filename;
    viewerDocMeta.textContent = `Processed via ${doc.device.toUpperCase()} at ${doc.timestamp}`;
    
    // Add warning banner if one is present
    let warningBanner = "";
    if (doc.warning) {
      warningBanner = `
        <blockquote class="warning">
          <strong>Pipeline Notification:</strong><br>
          ${doc.warning}
        </blockquote>
      `;
    }

    markdownRenderer.innerHTML = warningBanner + parseMarkdown(doc.text);
    viewerActions.style.display = "flex";
  }

  function renderErrorState(errText) {
    viewerDocTitle.textContent = "Extraction Failed";
    viewerDocMeta.textContent = "Error log";
    viewerActions.style.display = "none";
    
    markdownRenderer.innerHTML = `
      <div style="color: var(--color-danger); padding: 1rem; border: 1px solid rgba(239, 68, 68, 0.2); border-radius: var(--radius-sm); background: rgba(239, 68, 68, 0.05);">
        <h3><i data-lucide="alert-triangle" style="vertical-align: middle; margin-right: 0.5rem;"></i> pipeline_failure_error</h3>
        <p style="margin-top: 0.5rem; font-family: var(--font-mono); font-size: 0.85rem;">${errText}</p>
      </div>
    `;
    lucide.createIcons();
  }

  // --- Smart Client-Side Markdown Parser ---
  function parseMarkdown(md) {
    if (!md) return "";
    
    let html = md;
    
    // Escape HTML characters to prevent XSS issues
    html = html
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Code blocks
    html = html.replace(/```([\s\S]*?)```/g, (match, code) => {
      return `<pre><code>${code.trim()}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`\n]+)`/g, "<code>$1</code>");

    // Headers
    html = html.replace(/^# (.*$)/gim, "<h1>$1</h1>");
    html = html.replace(/^## (.*$)/gim, "<h2>$1</h2>");
    html = html.replace(/^### (.*$)/gim, "<h3>$1</h3>");

    // Blockquotes
    html = html.replace(/^\&gt;\s*\[\!WARNING\](.*$)/gim, '<blockquote class="warning"><strong>Warning</strong>');
    html = html.replace(/^\&gt;\s*\[\!IMPORTANT\](.*$)/gim, '<blockquote class="warning"><strong>Important</strong>');
    html = html.replace(/^\&gt;\s*\[\!NOTE\](.*$)/gim, '<blockquote><strong>Note</strong>');
    html = html.replace(/^\&gt;\s*(.*$)/gim, "<blockquote>$1</blockquote>");
    
    // Combine sequential blockquotes safely
    html = html.replace(/<\/blockquote>\s*<blockquote>/g, "<br>");

    // Unordered lists
    html = html.replace(/^\s*-\s+(.*$)/gim, "<li>$1</li>");
    // Wrap lists in ul
    html = html.replace(/(<li>[\s\S]*?<\/li>)/g, "<ul>$1</ul>");
    html = html.replace(/<\/ul>\s*<ul>/g, "");

    // Bold text
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

    // Linebreaks
    html = html.replace(/\n\n/g, "<p></p>");
    html = html.replace(/\n/g, "<br>");

    return html;
  }

  // --- Recent Extraction Sidebar ---
  function updateHistoryUI() {
    if (recentExtractions.length === 0) {
      historyEmpty.style.display = "block";
      return;
    }
    historyEmpty.style.display = "none";
    
    // Map items to nodes
    historyContainer.innerHTML = recentExtractions.map(doc => {
      const isSelected = doc.id === activeExtractionId ? "active" : "";
      const devClass = doc.device === "cuda" || doc.device === "gpu" ? "device-cuda" : "device-cpu";
      const devLabel = doc.device.toUpperCase() === "CUDA" ? "GPU" : doc.device.toUpperCase();
      
      return `
        <div class="history-item ${isSelected}" data-id="${doc.id}">
          <div class="history-info">
            <span class="history-name">${doc.filename}</span>
            <div class="history-meta">
              <span>${doc.timestamp}</span>
              <span class="history-device-tag ${devClass}">${devLabel}</span>
            </div>
          </div>
        </div>
      `;
    }).join("");

    // Setup history click listeners
    const items = historyContainer.querySelectorAll(".history-item");
    items.forEach(item => {
      item.addEventListener("click", () => {
        const docId = item.getAttribute("data-id");
        activeExtractionId = docId;
        
        // Highlight active sidebar item
        items.forEach(i => i.classList.remove("active"));
        item.classList.add("active");
        
        // Load in viewer
        const selectedDoc = recentExtractions.find(d => d.id === docId);
        if (selectedDoc) {
          renderDocument(selectedDoc);
        }
      });
    });
  }

  // --- Copy & Download Actions ---
  copyBtn.addEventListener("click", () => {
    const activeDoc = recentExtractions.find(d => d.id === activeExtractionId);
    if (!activeDoc) return;

    navigator.clipboard.writeText(activeDoc.text)
      .then(() => {
        showToast("Markdown text copied to clipboard!", "success", "clipboard-check");
      })
      .catch(() => {
        showToast("Failed to copy text.", "danger", "alert-circle");
      });
  });

  downloadBtn.addEventListener("click", () => {
    const activeDoc = recentExtractions.find(d => d.id === activeExtractionId);
    if (!activeDoc) return;

    const blob = new Blob([activeDoc.text], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    
    // Clean original filename and append md extension
    const baseName = activeDoc.filename.replace(/\.[^/.]+$/, "");
    link.href = url;
    link.download = `${baseName}_extracted.md`;
    document.body.appendChild(link);
    link.click();
    
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    showToast("Downloaded markdown file!", "success", "file-down");
  });

  // --- Custom Toast Alert Notification ---
  let toastTimeout;
  function showToast(message, type = "success", iconName = "info") {
    clearTimeout(toastTimeout);
    
    toastText.textContent = message;
    toast.className = `toast active ${type}`;
    
    // Set custom icon
    toastIcon.setAttribute("data-lucide", iconName);
    lucide.createIcons();

    toastTimeout = setTimeout(() => {
      toast.classList.remove("active");
    }, 4000);
  }
});
