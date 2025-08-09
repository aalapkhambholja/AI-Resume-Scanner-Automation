# bedrock_flask.py - Final version for selecting existing JDs

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import boto3
import os
import time
import requests

# --- Configuration ---
S3_BUCKET_NAME = 'agentic-ai-screener-data'
N8N_WEBHOOK_URL = 'https://adriani.app.n8n.cloud/webhook/4c813ee5-c489-4a54-b7c5-63ecfab488c8'
S3_JD_FOLDER = 'job-descriptions/'
S3_RESUMES_FOLDER = 'resumes/pending/'

# --- Initialize App & Boto3 ---
app = Flask(__name__)
CORS(app)
s3_client = boto3.client('s3')

# --- Route to serve the HTML frontend ---
@app.route("/")
def index():
    return render_template("resume.html")

# --- NEW: API Endpoint to list available Job Descriptions ---
@app.route("/get-jds")
def get_jds():
    try:
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=S3_JD_FOLDER)
        jds = []
        # Filter out the folder itself and get clean names
        for obj in response.get('Contents', []):
            if obj['Key'] != S3_JD_FOLDER:
                jds.append({
                    "key": obj['Key'],
                    "name": os.path.basename(obj['Key'])
                })
        return jsonify(jds)
    except Exception as e:
        print(f"Error listing JDs: {e}")
        return jsonify({"error": "Could not list job descriptions from S3"}), 500

# --- API Endpoint for Uploading Resumes and Triggering n8n ---
@app.route("/upload-and-trigger", methods=["POST"])
def upload_and_trigger():
    # 1. Get the selected JD key and resume files from the form data
    jd_key = request.form.get('jd_key')
    resume_files = request.files.getlist('resumes')

    if not jd_key or not resume_files:
        return jsonify({"error": "Job description and resumes are required."}), 400

    # 2. Generate a unique Batch ID
    batch_id = f"batch-{int(time.time())}"
    print(f"--- Starting new batch: {batch_id} for JD: {jd_key} ---")

    try:
        # 3. Upload all the resumes to a new 'pending' subfolder named after the batch
        for resume in resume_files:
            resume_s3_key = os.path.join(S3_RESUMES_FOLDER, resume.filename)
            s3_client.upload_fileobj(resume, S3_BUCKET_NAME, resume_s3_key)
            print(f"  - Uploaded resume to: {resume_s3_key}")
        
        print("All resumes for batch uploaded successfully.")
    except Exception as e:
        return jsonify({"error": f"Failed to upload resumes to S3: {str(e)}"}), 500

    # 4. Trigger the n8n workflow, passing both Batch ID and the selected JD Key
    print(f"Triggering n8n workflow for batch: {batch_id}...")
    try:
        webhook_payload = {
            'batchId': batch_id,
            'jobDescriptionKey': jd_key 
        }
        response = requests.post(N8N_WEBHOOK_URL, json=webhook_payload)
        response.raise_for_status()
        
        print("n8n workflow triggered successfully.")
        return jsonify({"message": "Successfully started analysis.", "batchId": batch_id}), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to trigger analysis workflow."}), 500

# --- Main execution block ---
if __name__ == "__main__":
    app.run(debug=True)