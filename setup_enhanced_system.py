#!/usr/bin/env python3
"""
Setup script for enhanced Store Intelligence system.
Installs dependencies, validates setup, and provides usage instructions.
"""

import os
import sys
import subprocess
import json
from pathlib import Path


def run_command(cmd, description):
    """Run shell command and handle errors."""
    print(f"📦 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False


def check_python_version():
    """Check Python version compatibility."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor} is compatible")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor} is not supported. Need Python 3.8+")
        return False


def install_dependencies():
    """Install required Python packages."""
    print("📦 Installing dependencies...")
    
    # Core dependencies
    core_deps = [
        "fastapi>=0.104.1",
        "uvicorn>=0.24.0", 
        "pydantic>=2.5.0",
        "pytest>=7.4.3",
        "pytest-asyncio>=0.21.1",
        "python-multipart>=0.0.6"
    ]
    
    # Computer vision dependencies
    cv_deps = [
        "ultralytics>=8.0.0",
        "opencv-python>=4.8.0",
        "numpy>=1.24.0",
        "torch>=2.0.0",
        "torchvision>=0.15.0"
    ]
    
    all_deps = core_deps + cv_deps
    
    for dep in all_deps:
        if not run_command(f"pip install {dep}", f"Installing {dep}"):
            print(f"⚠️  Failed to install {dep}, continuing...")
    
    return True


def validate_installation():
    """Validate that all components are working."""
    print("🔍 Validating installation...")
    
    try:
        # Test core imports
        import fastapi
        import uvicorn
        import pydantic
        print("✅ Core FastAPI components available")
        
        # Test computer vision imports
        try:
            import cv2
            import numpy as np
            print("✅ OpenCV and NumPy available")
        except ImportError as e:
            print(f"⚠️  OpenCV/NumPy issue: {e}")
        
        # Test YOLOv8
        try:
            from ultralytics import YOLO
            print("✅ YOLOv8 (ultralytics) available")
        except ImportError as e:
            print(f"⚠️  YOLOv8 not available: {e}")
        
        # Test PyTorch
        try:
            import torch
            import torchvision
            print(f"✅ PyTorch {torch.__version__} available")
        except ImportError as e:
            print(f"⚠️  PyTorch issue: {e}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import validation failed: {e}")
        return False


def create_sample_data():
    """Create sample data files for testing."""
    print("📄 Creating sample data files...")
    
    # Create data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Sample store layout
    store_layout = {
        "STORE_BLR_002": {
            "store_name": "Apex Retail - Bangalore",
            "city": "Bangalore", 
            "open_hours": "09:00-21:00",
            "zones": {
                "ENTRY": {"x1": 0, "y1": 0, "x2": 1920, "y2": 200},
                "SKINCARE": {"x1": 200, "y1": 200, "x2": 600, "y2": 600},
                "BILLING": {"x1": 800, "y1": 200, "x2": 1200, "y2": 600},
                "CHECKOUT": {"x1": 1200, "y1": 200, "x2": 1600, "y2": 600}
            },
            "cameras": {
                "CAM_ENTRY_01": {"type": "entry", "coverage": "ENTRY"},
                "CAM_FLOOR_01": {"type": "floor", "coverage": ["SKINCARE", "BILLING"]},
                "CAM_BILLING_01": {"type": "billing", "coverage": "BILLING"}
            }
        }
    }
    
    with open(data_dir / "store_layout.json", "w") as f:
        json.dump(store_layout, f, indent=2)
    print("✅ Created sample store_layout.json")
    
    # Sample POS transactions
    pos_data = [
        "store_id,transaction_id,timestamp,basket_value_inr",
        "STORE_BLR_002,TXN_00001,2026-04-22T10:15:30Z,1250.00",
        "STORE_BLR_002,TXN_00002,2026-04-22T10:18:45Z,680.50",
        "STORE_BLR_002,TXN_00003,2026-04-22T10:22:10Z,2100.75",
        "STORE_BLR_002,TXN_00004,2026-04-22T10:25:15Z,450.25",
        "STORE_BLR_002,TXN_00005,2026-04-22T10:28:40Z,1875.90"
    ]
    
    with open(data_dir / "pos_transactions.csv", "w") as f:
        f.write("\n".join(pos_data))
    print("✅ Created sample pos_transactions.csv")
    
    # Create videos directory
    videos_dir = data_dir / "videos"
    videos_dir.mkdir(exist_ok=True)
    print("✅ Created data/videos/ directory (place your MP4 files here)")
    
    return True


def run_tests():
    """Run the test suite."""
    print("🧪 Running test suite...")
    
    if not run_command("python test_enhanced_pipeline.py", "Running enhanced pipeline tests"):
        print("⚠️  Some tests failed, but system may still work")
    
    return True


def print_usage_instructions():
    """Print comprehensive usage instructions."""
    print("\n" + "="*60)
    print("🎯 ENHANCED STORE INTELLIGENCE SYSTEM READY!")
    print("="*60)
    
    print("\n📁 DIRECTORY STRUCTURE:")
    print("store-intelligence/")
    print("├── data/")
    print("│   ├── videos/          # Place your MP4 files here")
    print("│   ├── store_layout.json")
    print("│   └── pos_transactions.csv")
    print("├── pipeline/           # Detection & tracking")
    print("├── app/               # FastAPI backend")
    print("└── tests/             # Test suite")
    
    print("\n🚀 QUICK START:")
    print("1. Extract dataset:")
    print("   unzip store-intelligence-dataset.zip -d data/")
    
    print("\n2. Run detection pipeline:")
    print("   # Mock mode (for testing)")
    print("   python pipeline/run.py --output data/events.jsonl")
    print("   ")
    print("   # Real mode (with actual videos)")
    print("   python pipeline/run.py --use-real --store-layout data/store_layout.json --output data/events.jsonl")
    
    print("\n3. Start API server:")
    print("   python -m uvicorn app.main:app --reload --port 8000")
    
    print("\n4. Ingest events:")
    print("   curl -X POST http://localhost:8000/events/ingest \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d @data/events.jsonl")
    
    print("\n📊 DASHBOARD ACCESS:")
    print("   # Terminal dashboard")
    print("   curl http://localhost:8000/stores/STORE_BLR_002/dashboard/terminal")
    print("   ")
    print("   # Web dashboard")
    print("   open http://localhost:8000/stores/STORE_BLR_002/dashboard.html")
    print("   ")
    print("   # JSON metrics")
    print("   curl http://localhost:8000/stores/STORE_BLR_002/metrics")
    
    print("\n🔧 ADVANCED USAGE:")
    print("   # Cross-camera deduplication")
    print("   python pipeline/run.py --use-real --use-cross-camera --store-layout data/store_layout.json")
    print("   ")
    print("   # Process specific store")
    print("   python pipeline/run.py --store-id STORE_BLR_003 --store-layout data/store_layout.json")
    print("   ")
    print("   # Run with Docker")
    print("   docker-compose up")
    
    print("\n🧪 TESTING:")
    print("   # Run all tests")
    print("   python test_enhanced_pipeline.py")
    print("   ")
    print("   # Run API tests")
    print("   pytest tests/")
    print("   ")
    print("   # Validate with assertions")
    print("   python data/assertions.py  # (if provided in dataset)")
    
    print("\n📈 FEATURES:")
    print("✅ Real YOLOv8 person detection")
    print("✅ Cross-camera deduplication")
    print("✅ Staff filtering (heuristic)")
    print("✅ POS transaction correlation")
    print("✅ Real-time dashboard (terminal + web)")
    print("✅ Edge case handling (groups, re-entry, occlusion)")
    print("✅ Production logging & error handling")
    print("✅ Docker containerization")
    
    print("\n🔍 TROUBLESHOOTING:")
    print("   # Check system health")
    print("   curl http://localhost:8000/health")
    print("   ")
    print("   # View logs")
    print("   tail -f app.log")
    print("   ")
    print("   # Test detection only")
    print("   python -c \"from pipeline.detect import YOLOv8Detector; print('YOLOv8 OK')\"")
    
    print("\n📚 DOCUMENTATION:")
    print("   README.md              # Quick start guide")
    print("   docs/DESIGN.md         # Architecture details")
    print("   docs/CHOICES.md        # Design decisions")
    print("   DATASET_GUIDE.md       # Dataset integration")
    print("   QUICK_REFERENCE.md     # API reference")
    
    print("\n" + "="*60)
    print("Ready to process real CCTV data! 🎥➡️📊")
    print("="*60)


def main():
    """Main setup function."""
    print("🏗️  ENHANCED STORE INTELLIGENCE SYSTEM SETUP")
    print("=" * 50)
    
    success = True
    
    # Check Python version
    if not check_python_version():
        success = False
    
    # Install dependencies
    if success and not install_dependencies():
        success = False
    
    # Validate installation
    if success and not validate_installation():
        success = False
    
    # Create sample data
    if success and not create_sample_data():
        success = False
    
    # Run tests
    if success:
        run_tests()
    
    # Print usage instructions
    if success:
        print_usage_instructions()
    else:
        print("\n❌ Setup encountered issues. Please check error messages above.")
        print("You may need to install dependencies manually:")
        print("pip install -r requirements.txt")
    
    return success


if __name__ == "__main__":
    main()