# Chewbacca: Intelligent Task Scheduler

This project is a full-stack application featuring a Flask backend and a React/Vite/TypeScript frontend for intelligent task scheduling.

## Project Structure

The project is organized into two main parts:

- `backend/`: Contains the Flask application, including API routes, database models, and the core scheduling logic.
- `frontend/`: Contains the React application built with Vite, TypeScript, and Shadcn UI.

## Quick Setup

A setup script is provided to automate the installation process.

```bash
# Make the script executable
chmod +x setup.sh

# Run the setup script
./setup.sh
```

This script will:

1. Create and activate a Python virtual environment in `/venv`.
2. Install Python dependencies from `backend/requirements.txt`.
3. Initialize and upgrade the database using Flask-Migrate.
4. Install frontend dependencies using `npm`.
5. Start both the backend and frontend development servers.

- **Backend API:** `http://localhost:5002`
- **Frontend App:** `http://localhost:5173`

Press `Ctrl+C` in the terminal to stop both servers.

If you prefer to set up the project manually, follow these steps:

### Backend Setup

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r backend/requirements.txt

# Initialize the database (if it doesn't exist)
flask db init --directory backend/migrations
flask db upgrade --directory backend/migrations

# Run the Flask backend server
flask run --host=0.0.0.0 --port=5002
```

### Frontend Setup

```bash
# Navigate to the frontend directory
cd frontend

# Install NPM dependencies
npm install

# Start the development server
npm run dev
```

## Accessing the Application

- Backend API: http://localhost:5002
- Frontend: http://localhost:5173
# chewy
