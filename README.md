# Chewbacca Project

## Quick Setup

```bash
# Make the script executable
chmod +x setup.sh

# Run the setup script
./setup.sh
```

By default the app will be available at http://localhost:5173 (unless you have some other service running on that port, in which case it will be on the next available port). The backend will be available at http://localhost:5002.

## What the Setup Scripts Do

The setup scripts automate the following tasks:

1. Create a Python virtual environment (if it doesn't exist)
2. Install Python dependencies from requirements.txt
3. Initialize the SQLite database (if it doesn't exist)
4. Install frontend NPM dependencies
5. Start both the Flask backend server and React/Vite frontend server

Both servers will run in the current terminal. To stop both servers, simply press `Ctrl+C` in the terminal where you started the setup script.

## Manual Setup

If you prefer to set up the project manually, follow these steps:

### Backend Setup

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Initialize the database (if it doesn't exist)
flask db init
flask db upgrade

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
