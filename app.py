import os
import json
import uuid
import threading
import time
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from engines.parser import get_hardware_status, parse_document, CONFIG_PATH

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB Max upload size

# Ensure upload directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# In-memory store for processing tasks
TASKS = {}

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"device": "auto"}

def save_config(config_data):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(config_data, f, indent=2)
        return True
    except Exception:
        return False

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "POST":
        data = request.json or {}
        device = data.get("device", "auto")
        if device not in ["auto", "cpu", "gpu"]:
            return jsonify({"success": False, "error": "Invalid device selection"}), 400
            
        config = {"device": device}
        if save_config(config):
            return jsonify({
                "success": True,
                "config": config,
                "hardware_status": get_hardware_status()
            })
        return jsonify({"success": False, "error": "Failed to write config file"}), 500
        
    # GET request
    config = load_config()
    hw_status = get_hardware_status()
    return jsonify({
        "success": True,
        "config": config,
        "hardware_status": hw_status
    })

def async_parse_task(task_id, file_path):
    TASKS[task_id] = {
        "status": "processing",
        "progress": 15,
        "message": "Uploading and caching document...",
        "result": None
    }
    
    try:
        # Realistic transitions to keep frontend dynamic
        time.sleep(0.4)
        TASKS[task_id]["progress"] = 35
        TASKS[task_id]["message"] = "Initializing parsing pipelines..."
        
        time.sleep(0.4)
        TASKS[task_id]["progress"] = 65
        TASKS[task_id]["message"] = "Running deep layout analysis & OCR..."
        
        # Run actual docling parser engine
        res = parse_document(file_path)
        
        if res.get("success"):
            TASKS[task_id] = {
                "status": "completed",
                "progress": 100,
                "message": "Extraction complete.",
                "result": {
                    "text": res["text"],
                    "device_used": res["device_used"],
                    "warning": res.get("warning")
                }
            }
        else:
            TASKS[task_id] = {
                "status": "failed",
                "progress": 100,
                "message": "Extraction failed.",
                "error": res.get("error", "Unknown parser error")
            }
    except Exception as e:
        TASKS[task_id] = {
            "status": "failed",
            "progress": 100,
            "message": "System error occurred.",
            "error": str(e)
        }
    finally:
        # Secure cleanup of uploaded PDF
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass

@app.route("/api/upload", methods=["POST"])
def api_upload():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part in request"}), 400
        
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No selected file"}), 400
        
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "error": "Unsupported file format. Only PDFs allowed."}), 400
        
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
    
    try:
        file.save(file_path)
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to save uploaded file: {str(e)}"}), 500
        
    task_id = str(uuid.uuid4())
    
    # Launch async processing in a background worker thread
    thread = threading.Thread(target=async_parse_task, args=(task_id, file_path))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "task_id": task_id,
        "filename": filename
    })

@app.route("/api/status/<task_id>", methods=["GET"])
def api_status(task_id):
    task = TASKS.get(task_id)
    if not task:
        return jsonify({"success": False, "error": "Task session not found"}), 404
    return jsonify({"success": True, "task": task})

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
