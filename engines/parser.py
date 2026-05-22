import os
import json

# Lazy loading torch and docling to prevent startup lag or crashes
DOCLING_AVAILABLE = False
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
    DOCLING_AVAILABLE = True
except ImportError:
    pass

TORCH_AVAILABLE = False
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    pass

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"device": "auto"}

def get_hardware_status():
    cuda_available = False
    gpu_name = None
    
    if TORCH_AVAILABLE:
        try:
            cuda_available = torch.cuda.is_available()
            if cuda_available:
                gpu_name = torch.cuda.get_device_name(0)
        except Exception:
            pass
            
    return {
        "cuda_available": cuda_available,
        "gpu_name": gpu_name,
        "docling_available": DOCLING_AVAILABLE,
        "torch_available": TORCH_AVAILABLE
    }

def parse_document(file_path):
    config = load_config()
    device_setting = config.get("device", "auto")
    
    hw_status = get_hardware_status()
    cuda_available = hw_status["cuda_available"]
    
    # Resolve physical device
    resolved_device = "cpu"
    warning = None
    
    if device_setting == "gpu" or device_setting == "cuda":
        if cuda_available:
            resolved_device = "cuda"
        else:
            resolved_device = "cpu"
            warning = "Requested GPU processing, but NVIDIA CUDA is not available on this system. Fell back to CPU."
    elif device_setting == "auto":
        resolved_device = "cuda" if cuda_available else "cpu"
    else:
        resolved_device = "cpu"
        
    if not DOCLING_AVAILABLE:
        # Graceful fallback: return mock document structure so application remains functional and testable
        filename = os.path.basename(file_path)
        mock_markdown = f"""# Document Extraction: {filename}

> [!WARNING]
> **Docling Library Not Detected:** Processing was completed using the lightweight simulated engine.

## Metadata
- **File Name:** {filename}
- **Target Device Setting:** `{device_setting.upper()}`
- **Resolved Run Device:** `{resolved_device.upper()}`
- **CUDA Capability Detected:** `{cuda_available}`
- **PyTorch Installed:** `{TORCH_AVAILABLE}`

---

## Simulated Extraction Output
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. 
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

### System Configuration Instructions
To enable full-fidelity layout extraction using IBM's Docling engine on your selected hardware (`{resolved_device}`):
1. Install PyTorch with CUDA (if using GPU):
   ```bash
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
   ```
2. Install Docling:
   ```bash
   pip install docling
   ```
"""
        return {
            "success": True,
            "text": mock_markdown,
            "device_used": resolved_device,
            "warning": warning or "Docling is not installed. Running in simulation mode."
        }
        
    try:
        from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
        
        acc_device = AcceleratorDevice.CUDA if resolved_device == "cuda" else AcceleratorDevice.CPU
        
        accelerator_options = AcceleratorOptions(device=acc_device)
        converter = DocumentConverter(accelerator_options=accelerator_options)
        
        result = converter.convert(file_path)
        extracted_markdown = result.document.export_to_markdown()
        
        return {
            "success": True,
            "text": extracted_markdown,
            "device_used": resolved_device,
            "warning": warning
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "device_used": resolved_device
        }
