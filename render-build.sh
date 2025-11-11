git ls-files --stage render-build.shset -o errexit

echo "=== Installing Tesseract OCR ==="
apt-get update
apt-get install -y tesseract-ocr tesseract-ocr-eng

echo "=== Verifying Tesseract Installation ==="
tesseract --version

echo "=== Installing Python Dependencies ==="
pip install -r requirements.txt

echo "=== Build Complete ==="