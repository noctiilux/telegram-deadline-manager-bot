# 🕒 Telegram Deadline Manager Bot

📋 *[Читать на русском языке](README_RU.md)*

---

An asynchronous Telegram bot designed to manage student tasks, track project milestones, and send automated deadline reminders. Built natively to support both personal time management and synchronized group chat workflows.

## 🛠️ Tech Stack & Features
*   **Language/Framework:** Python 3 + `aiogram`.
*   **Data Structure & Logging:** Structural internal state logic for managing user context and operational records.
*   **Core Automation Functions:** 
    *   Add, view, edit, and delete active deadlines with strict temporal validation.
    *   Group chat integration — keeps dynamic project teams synced on upcoming milestones.
    *   Automated push-notifications before a tracked deadline expires.

## 📁 Repository Structure

*   `/uni_bot` — Core Python application package containing handlers, states, and business controllers.
*   `requirements` — Configuration file mapping package dependencies required for clean application builds.
