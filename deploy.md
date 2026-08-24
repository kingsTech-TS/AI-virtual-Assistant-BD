# Deployment Guide: GitHub & Render

This guide provides step-by-step instructions for pushing the **Academic Virtual Chatbot Backend** codebase to **GitHub** and deploying it as a live web service on **Render**.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Part 1: Pushing Code to GitHub](#part-1-pushing-code-to-github)
3. [Part 2: Deploying to Render](#part-2-deploying-to-render)
   - [Option A: Python Native Web Service (Recommended)](#option-a-python-native-web-service-recommended)
   - [Option B: Docker Container Web Service](#option-b-docker-container-web-service)
4. [Part 3: Setting Up Environment Variables](#part-3-setting-up-environment-variables)
5. [Part 4: Database & Access Control (MongoDB Atlas)](#part-4-database--access-control-mongodb-atlas)
6. [Part 5: Verification & Continuous Deployment](#part-5-verification--continuous-deployment)

---

## Prerequisites

Before starting, ensure you have:
* A **[GitHub](https://github.com/)** account.
* A **[Render](https://render.com/)** account.
* A hosted **[MongoDB Atlas](https://www.mongodb.com/cloud/atlas)** database URI.
* Git installed locally.

---

## Part 1: Pushing Code to GitHub

### Step 1: Verify Git Status and Exclusions
Make sure your `.gitignore` file is updated so sensitive files like `.env`, `venv/`, and `.claude/` are not committed.

Run the following command in your terminal:
```bash
git status
```

### Step 2: Create a New GitHub Repository
1. Log in to [GitHub](https://github.com/).
2. Click the **+** icon in the top right corner and select **New repository**.
3. Fill in the repository details:
   * **Repository name**: `academic-virtual-backend` (or your preferred name)
   * **Visibility**: Public or Private
   * **Initialize repository**: Do **NOT** check "Add a README file" or `.gitignore` (we already have local versions).
4. Click **Create repository**.

### Step 3: Initialize Git and Stage Files
If git is not already initialized in your project folder, run:
```bash
git init
```

Stage all project files:
```bash
git add .
```

Create your initial commit:
```bash
git commit -m "Initial commit - FastAPI Academic Virtual Chatbot Backend"
```

### Step 4: Link Local Repository to GitHub and Push
Copy your remote repository URL from GitHub, then execute:

```bash
git branch -M main
git remote add origin https://github.com/<your-username>/academic-virtual-backend.git
git push -u origin main
```

*(Replace `<your-username>` with your actual GitHub username).*

---

## Part 2: Deploying to Render

Render allows deploying FastAPI either as a native **Python Web Service** or as a **Docker container**.

### Option A: Python Native Web Service (Recommended)

1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** in the top right and select **Web Service**.
3. Under **Connect a repository**, select your GitHub repository (`academic-virtual-backend`).
4. Configure the Web Service settings:

| Setting | Value |
| :--- | :--- |
| **Name** | `academic-virtual-backend` |
| **Language / Runtime** | `Python 3` |
| **Region** | Choose the closest region (e.g., Oregon, Frankfurt, Singapore) |
| **Branch** | `main` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | Free (or Starter/Standard) |

---

### Option B: Docker Container Web Service

Since the codebase includes a `Dockerfile`, you can also deploy as a Docker service:

1. Click **New +** -> **Web Service** on Render.
2. Select your GitHub repository.
3. Set the runtime environment:
   * **Runtime / Language**: `Docker`
   * **Dockerfile Path**: `./Dockerfile`
   * **Docker Context**: `.`
4. Render will automatically detect the Dockerfile and use `EXPOSE 8000` / `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`.

---

## Part 3: Setting Up Environment Variables

In your Render service configuration, scroll down to the **Environment Variables** section (or navigate to **Environment** tab after creation) and add the following keys:

| Key | Example Value / Description | Required? |
| :--- | :--- | :--- |
| `APP_NAME` | `Academic Support Chatbot` | Yes |
| `APP_ENV` | `production` | Yes |
| `DEBUG` | `false` | Yes |
| `MONGODB_URI` | `mongodb+srv://<user>:<password>@<cluster>.mongodb.net/...` | **Yes** |
| `MONGODB_DATABASE` | `academic_chatbot` | Yes |
| `JWT_SECRET_KEY` | *(Generate a 32-byte hex string)* | **Yes** |
| `JWT_ALGORITHM` | `HS256` | Yes |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Yes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Yes |
| `FRONTEND_URL` | `https://your-frontend.onrender.com` | Yes |
| `LLM_API_KEY` | *(Your LLM API Key, if using Vercel AI Gateway / OpenAI / Grok)* | Optional |
| `LLM_MODEL` | `xai/grok-4.6` | Optional |
| `LLM_BASE_URL` | `https://ai-gateway.vercel.sh/v1` | Optional |
| `USE_LLM_INTENT` | `false` | Optional |
| `USE_QUERY_EMBEDDINGS` | `false` | Optional |

> 🔑 **Generating a Secure JWT Secret Key**:
> You can generate a random 32-byte secret key by running this in Python:
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

---

## Part 4: Database & Access Control (MongoDB Atlas)

Render dynamically assigns dynamic IP addresses to free and standard instances. Ensure MongoDB Atlas allows connections from Render:

1. Log into **[MongoDB Atlas](https://cloud.mongodb.com/)**.
2. Navigate to **Network Access** under the **Security** section on the left sidebar.
3. Click **Add IP Address**.
4. Select **Allow Access from Anywhere** (`0.0.0.0/0`) or configure Render's outbound static IPs (available on paid Render plans).
5. Click **Confirm**.

---

## Part 5: Verification & Continuous Deployment

### 1. Finalizing Deployment
Click **Create Web Service** (or **Save Changes**). Render will clone your GitHub repo, run the build command, set up environment variables, and start the service.

### 2. Verifying Health Check and Documentation
Once the build status shows **Live**:
* **Root Endpoint**: Open `https://<your-service-name>.onrender.com/` in your browser. You should receive:
  ```json
  {
    "success": true,
    "data": {
      "status": "ok",
      "app_name": "Academic Support Chatbot"
    }
  }
  ```
* **Swagger API Docs**: Open `https://<your-service-name>.onrender.com/docs` to test interactive endpoints.

### 3. Continuous Deployment (Automatic Builds)
Render automatically connects to your GitHub repository webhook. Every time you push new commits to the `main` branch:
```bash
git add .
git commit -m "feat: updated API endpoints"
git push origin main
```
Render will automatically trigger a clean rebuild and zero-downtime re-deployment!
