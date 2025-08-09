# AI Resume Scanner

AI Resume Scanner is a multi-service AI-powered application designed to help HR and management teams process and analyze resumes efficiently. The project consists of three Streamlit dashboards for different user roles and a Flask backend API, all integrated with AWS services for data management and authentication.

## Features

- **Main App (`new_app.py`)**: Streamlit interface running on port 8501 for general resume scanning and processing.
- **HR Dashboard (`new_hr.py`)**: Streamlit dashboard running on port 8502 to manage candidates, view analytics, and communicate with applicants.
- **Manager Dashboard (`new_manager.py`)**: Streamlit dashboard running on port 8503 to review resumes, track candidate progress, and generate reports.
- **Backend API (`resume.py`)**: Flask application running on port 5000 to handle backend logic, serve APIs, and manage AWS DynamoDB interactions.
- AWS Cognito authentication integration via `streamlit_cognito_auth`.
- Uses AWS SDK for Python (`boto3`) for accessing AWS services securely.
- Fully Dockerized with separate containers for each app managed via Docker Compose.

## Folder Structure

<pre> ```plaintext AI-Resume-Scanner/ ├── new_app.py ├── new_hr.py ├── new_manager.py ├── resume.py ├── templates/ │ └── resume.html ├── Dockerfile.streamlit ├── Dockerfile.flask ├── docker-compose.yml ├── requirements_streamlit.txt ├── requirements_flask.txt ├── .env └── README.md ``` </pre>

## Create a .env file with your AWS credentials:
AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
