#!/bin/bash
# Check model file integrity

echo "=== Model Integrity Check ==="

MODEL_FILE="/home/nexus/Argos_Chatgpt/models/gguf/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"

if [ ! -f "$MODEL_FILE" ]; then
    echo "❌ Model file not found: $MODEL_FILE"
    exit 1
fi

echo "✅ Model file exists"

# Check file size
SIZE=$(stat -c%s "$MODEL_FILE" 2>/dev/null || stat -f%z "$MODEL_FILE" 2>/dev/null)
if [ -n "$SIZE" ]; then
    SIZE_MB=$((SIZE / 1024 / 1024))
    echo "📏 Model size: ${SIZE_MB}MB"
else
    echo "⚠️ Could not determine file size"
fi

# Check if file is readable
if [ -r "$MODEL_FILE" ]; then
    echo "✅ Model file is readable"
else
    echo "❌ Model file is not readable"
    exit 1
fi

# Check file header (GGUF files start with "GGUF")
HEADER=$(head -c 4 "$MODEL_FILE" 2>/dev/null | od -c 2>/dev/null | head -1)
if echo "$HEADER" | grep -q "G   G   U   F"; then
    echo "✅ Model appears to be valid GGUF format"
else
    echo "❌ Model does not appear to be valid GGUF format"
    echo "Header: $HEADER"
fi

# Try to read first few bytes
echo "📖 First few bytes:"
head -c 64 "$MODEL_FILE" | od -c 2>/dev/null | head -3

echo ""
echo "If model looks good, the issue might be:"
echo "1. Binary library dependencies"
echo "2. GPU/ROCm configuration"
echo "3. Memory allocation issues"