AI Resume Scanner

A multi-service AI-powered resume processing application consisting of three Streamlit dashboards (HR, Manager, and Main app) and a Flask backend API. The solution integrates AWS services via boto3 for data management, authentication with Cognito, and features resume parsing, candidate tracking, and analytics.

new_app.py: Main Streamlit app running on port 8501

new_hr.py: HR dashboard on port 8502

new_manager.py: Manager dashboard on port 8503

resume.py: Flask API backend running on port 5000

Uses AWS SDK for Python (boto3) to interact with AWS services securely

Dockerized with multi-container setup using Docker Compose for easy deployment
