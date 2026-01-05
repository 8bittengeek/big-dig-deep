#!/usr/bin/env bash
set -e

# 🧾 Arguments
PROJECT_NAME="big-web-archive"

echo "🚀 Bootstrapping project: $PROJECT_NAME"

# ----------------------------
# 📁 Create Project Structure
# ----------------------------
mkdir -p "$PROJECT_NAME"/{backend,crawler,qortal,qapp}
cd "$PROJECT_NAME"
echo "📂 Created project folders."

# ----------------------------
# 🐍 Python: virtualenv + deps
# ----------------------------
echo "🐍 Setting up Python environment..."
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install fastapi uvicorn playwright requests pydantic

# Install Playwright browsers
playwright install

echo "✔️ Python environment ready with FastAPI and Playwright!"
