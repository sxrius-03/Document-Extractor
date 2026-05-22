import unittest
from unittest.mock import patch
import os
import sys

# Add root folder to sys.path so we can import modules properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engines.parser import parse_document

class TestConfigResolution(unittest.TestCase):

    def setUp(self):
        # Force parser into simulation mode for logic verification to prevent file I/O or model loading
        self.docling_patcher = patch("engines.parser.DOCLING_AVAILABLE", False)
        self.docling_patcher.start()

    def tearDown(self):
        self.docling_patcher.stop()

    @patch("engines.parser.load_config")
    @patch("engines.parser.get_hardware_status")
    def test_cpu_device_resolution(self, mock_hw, mock_load_config):
        """Should always resolve to CPU when device config is explicitly cpu"""
        mock_load_config.return_value = {"device": "cpu"}
        mock_hw.return_value = {
            "cuda_available": True,  # Even if GPU is physically active
            "gpu_name": "NVIDIA RTX 4090",
            "docling_available": False,
            "torch_available": True
        }
        
        result = parse_document("dummy_file.pdf")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["device_used"], "cpu")
        # In simulation mode, the warning should indicate simulation fallback
        self.assertEqual(result.get("warning"), "Docling is not installed. Running in simulation mode.")

    @patch("engines.parser.load_config")
    @patch("engines.parser.get_hardware_status")
    def test_gpu_device_resolution_available(self, mock_hw, mock_load_config):
        """Should resolve to CUDA when device config is gpu and CUDA is available"""
        mock_load_config.return_value = {"device": "gpu"}
        mock_hw.return_value = {
            "cuda_available": True,
            "gpu_name": "NVIDIA RTX 4090",
            "docling_available": False,
            "torch_available": True
        }
        
        result = parse_document("dummy_file.pdf")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["device_used"], "cuda")

    @patch("engines.parser.load_config")
    @patch("engines.parser.get_hardware_status")
    def test_gpu_device_resolution_unavailable_fallback(self, mock_hw, mock_load_config):
        """Should fallback to CPU and raise a warning when device config is gpu but CUDA is unavailable"""
        mock_load_config.return_value = {"device": "gpu"}
        mock_hw.return_value = {
            "cuda_available": False,
            "gpu_name": None,
            "docling_available": False,
            "torch_available": True
        }
        
        result = parse_document("dummy_file.pdf")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["device_used"], "cpu")
        self.assertIn("Fell back to CPU", result["warning"])

    @patch("engines.parser.load_config")
    @patch("engines.parser.get_hardware_status")
    def test_auto_device_resolution_gpu_active(self, mock_hw, mock_load_config):
        """Should resolve to CUDA automatically if device is auto and CUDA is available"""
        mock_load_config.return_value = {"device": "auto"}
        mock_hw.return_value = {
            "cuda_available": True,
            "gpu_name": "NVIDIA A10G",
            "docling_available": False,
            "torch_available": True
        }
        
        result = parse_document("dummy_file.pdf")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["device_used"], "cuda")

    @patch("engines.parser.load_config")
    @patch("engines.parser.get_hardware_status")
    def test_auto_device_resolution_gpu_inactive(self, mock_hw, mock_load_config):
        """Should resolve to CPU automatically if device is auto and CUDA is unavailable"""
        mock_load_config.return_value = {"device": "auto"}
        mock_hw.return_value = {
            "cuda_available": False,
            "gpu_name": None,
            "docling_available": False,
            "torch_available": False
        }
        
        result = parse_document("dummy_file.pdf")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["device_used"], "cpu")

if __name__ == "__main__":
    unittest.main()
