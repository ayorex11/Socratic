#!/bin/bash
set -o errexit

echo "=== Updating package lists ==="
apt-get update

echo "=== Installing Tesseract OCR and dependencies ==="
apt-get install -y tesseract-ocr tesseract-ocr-eng libgl1-mesa-glx libsm6 libxrender1 libxext6

echo "=== Verifying Tesseract Installation ==="
which tesseract
tesseract --version

echo "=== Installing Python Dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Build Complete ==="