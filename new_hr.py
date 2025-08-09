import streamlit as st
import boto3
import pandas as pd
import plotly.express as px
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from fpdf import FPDF
import os

# Initialize DynamoDB resources
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('Resume_Matches')

# Initialize AWS SES client
ses_client = boto3.client('ses', region_name='us-east-1')

st.set_page_config(page_title="HR Dashboard", layout="wide")

# CSS styling (same as your original)
st.markdown("""
<style>
/* Overall app background - softer gradient for elegance */
.stApp {
    background: linear-gradient(135deg, #faf9f6, #f0f4f8);
    font-family: 'Segoe UI', sans-serif;
}
/* Header styling */
h1, h2, h3 {
    color: #1b1f3b;
    font-weight: bold;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.05);
}
/* Sidebar styling */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1565c0, #ff8f00);
    color: white;
    padding: 15px;
}
[data-testid="stSidebar"] * {
    color: white !important;
}
/* Buttons */
.stButton>button {
    background: linear-gradient(90deg, #0d47a1, #1976d2);
    color: white;
    border: none;
    border-radius: 6px;
    padding: 0.5em 1em;
    font-weight: bold;
    transition: 0.3s;
}
.stButton>button:hover {
    background: linear-gradient(90deg, #1976d2, #0d47a1);
    transform: scale(1.03);
}
/* KPI metrics */
[data-testid="stMetricValue"] {
    color: #1a237e;
    font-weight: bold;
}
[data-testid="stMetric"] {
    background: white;
    border-radius: 12px;
    padding: 12px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.08);
}
/* Badges */
.badge {
    display: inline-block;
    padding: 0.4em 0.85em;
    font-size: 0.85em;
    font-weight: 600;
    border-radius: 20px;
    color: white;
    margin-right: 5px;
    box-shadow: 0 3px 6px rgba(0,0,0,0.15);
}
.badge-strong { background-color: #43a047; }
.badge-moderate { background-color: #ffb300; }
.badge-weak { background-color: #e53935; }
.badge-approved { background-color: #6a1b9a; }
/* Table */
table {
    border-collapse: collapse;
    width: 100%;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 4px 15px rgba(0,0,0,0.08);
}
thead {
    background-color: #0d47a1;
    color: white;
    font-size: 1em;
}
tbody tr:nth-child(even) {
    background-color: #f4f6f8;
}
tbody tr:hover {
    background-color: #fff3e0;
    cursor: pointer;
}
/* Charts */
.js-plotly-plot {
    margin-bottom: 25px;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)
def fetch_candidates():
    try:
        response = table.scan()
        return response['Items']
    except Exception as e:
        st.error(f"Error fetching candidates: {e}")
        return []


def get_badge_html(rec):
    rec_lower = rec.lower()
    if rec_lower == 'strong':
        cls = 'badge-strong'
    elif rec_lower == 'moderate':
        cls = 'badge-moderate'
    elif rec_lower == 'weak':
        cls = 'badge-weak'
    elif rec_lower == 'approved':
        cls = 'badge-approved'
    else:
        cls = 'badge-weak'
    return f'<span class="badge {cls}">{rec}</span>'


def filter_candidates(candidates, score_min, exp_filter, skill_filter):
    filtered = []
    exp_filter = exp_filter.lower()
    skill_filter = skill_filter.lower()
    for item in candidates:
        try:
            score = float(item.get('Score', 0))
            exp = str(item.get('ExpMatch', '')).lower()
            skill = str(item.get('SkillsMatch', '')).lower()
            if (score >= score_min and
                    exp_filter in exp and
                    skill_filter in skill):
                filtered.append(item)
        except:
            continue
    return filtered


def generate_offer_pdf(candidate_name, role, salary, output_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(0, 10, f"Offer Letter for {candidate_name}", ln=True, align='C')
    pdf.ln(10)
    pdf.multi_cell(0, 10, f"Dear {candidate_name},\n\n"
                           f"We are pleased to offer you the position of {role} at our company.\n"
                           f"The offered salary is ${salary} per annum.\n\n"
                           f"Please review the terms and conditions and respond to this offer.\n\n"
                           "Best regards,\n"
                           "HR Team\n")
    pdf.output(output_path)


def send_offer_email_with_pdf(to_email, candidate_name, pdf_path):
    sender_email = "vishalintern2025@gmail.com"  # Replace with your verified SES sender email
    subject = "Offer Letter from IT Expert"

    body_text = f"""Dear {candidate_name},

Congratulations! Please find attached your offer letter.

Best regards,
HR Team
"""

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = to_email

    msg.attach(MIMEText(body_text, 'plain'))

    try:
        with open(pdf_path, 'rb') as f:
            part = MIMEApplication(f.read(), _subtype="pdf")
            part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
            msg.attach(part)
    except FileNotFoundError:
        st.error(f"Offer letter PDF file not found at path: {pdf_path}")
        return False

    try:
        ses_client.send_raw_email(
            Source=sender_email,
            Destinations=[to_email],
            RawMessage={'Data': msg.as_string()}
        )
        return True
    except ClientError as e:
        st.error(f"Failed to send email: {e.response['Error']['Message']}")
        return False


def hr_dashboard():
    st.title("🎯 HR DASHBOARD")

    # Sidebar button to open Flask upload page in new tab
    if st.sidebar.button("Open Upload Page"):
        flask_upload_url = "http://localhost:5000/"  # Adjust if your Flask runs on different host/port
        st.markdown(f'[Click here to upload Resume & JD]({flask_upload_url}){{:target="_blank"}}',
                    unsafe_allow_html=True)
        st.info("Upload page will open in a new browser tab.")
        return

    # Sidebar Filters
    st.sidebar.header("🔍 Filters")
    score_threshold = st.sidebar.slider("Minimum Score", 0, 100, 0)
    exp_filter = st.sidebar.text_input("Experience Match filter (partial text)", "")
    skill_filter = st.sidebar.text_input("Skills Match filter (partial text)", "")
    st.sidebar.markdown("---")

    candidates = fetch_candidates()

    if not candidates:
        st.warning("No candidates found in DynamoDB.")
        return

    filtered = filter_candidates(candidates, score_threshold, exp_filter, skill_filter)
    if not filtered:
        st.warning("No candidates found matching the criteria.")
        return

    df = pd.DataFrame(filtered)
    df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)
    df['RecommendationBadge'] = df['Recommendation'].apply(get_badge_html)

    if 'Status' not in df.columns:
        df['Status'] = ''
    if 'ManagerComments' not in df.columns:
        df['ManagerComments'] = ''

    df['Status'] = df['Status'].fillna('N/A')
    df.loc[df['Status'].str.strip() == '', 'Status'] = 'N/A'
    df['ManagerComments'] = df['ManagerComments'].fillna('')

    def categorize_exp(exp_text):
        exp_text = str(exp_text).lower()
        if 'junior' in exp_text or 'entry' in exp_text:
            return 'Junior'
        elif 'senior' in exp_text or 'lead' in exp_text:
            return 'Senior'
        elif 'mid' in exp_text or 'intermediate' in exp_text:
            return 'Mid'
        else:
            return 'Other'

    df['ExpLevel'] = df['ExpMatch'].apply(categorize_exp)
    exp_counts = df['ExpLevel'].value_counts()

    st.subheader(f"Candidate Details ({len(df)})")
    st.write(
        df[['Name', 'Email', 'JDID', 'Score', 'ExpMatch', 'SkillsMatch', 'RecommendationBadge', 'Status', 'ManagerComments']]
        .sort_values(by='Score', ascending=False)
        .to_html(escape=False, index=False),
        unsafe_allow_html=True
    )

    st.subheader("Candidate Visualizations")
    col1, col2 = st.columns(2)

    rec_color_map = {
        'Strong': '#43A047',
        'Moderate': '#FFA726',
        'Weak': '#E53935',
        'Approved': '#7E57C2'
    }

    with col1:
        rec_counts = df['Recommendation'].value_counts()
        fig_rec = px.bar(
            x=rec_counts.index,
            y=rec_counts.values,
            labels={'x': 'Recommendation', 'y': 'Count'},
            title="Candidates by Recommendation",
            color=rec_counts.index,
            color_discrete_map=rec_color_map
        )
        st.plotly_chart(fig_rec, use_container_width=True)

    with col2:
        fig_score = px.histogram(
            df,
            x='Score',
            nbins=20,
            title="Score Distribution",
            color=df['Recommendation'],
            color_discrete_map=rec_color_map
        )
        st.plotly_chart(fig_score, use_container_width=True)

    total_candidates = len(df)
    num_approved = df['Recommendation'].str.lower().eq('approved').sum()
    avg_score = df['Score'].mean() if total_candidates > 0 else 0

    st.markdown("---")
    st.subheader("📊 Dashboard KPIs")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total Candidates", total_candidates)
    kpi2.metric("Number Approved", num_approved)
    kpi3.metric("Average Score", f"{avg_score:.2f}")

    st.subheader("Candidates by Experience Level")
    fig_exp = px.bar(
        x=exp_counts.index,
        y=exp_counts.values,
        labels={'x': 'Experience Level', 'y': 'Count'},
        title="Candidate Distribution by Experience Level",
        color=exp_counts.index,
        color_discrete_map={
            'Junior': '#42A5F5',
            'Mid': '#66BB6A',
            'Senior': '#EF5350',
            'Other': '#AB47BC'
        }
    )
    st.plotly_chart(fig_exp, use_container_width=True)

    st.subheader("Send Offer Letters")

    hired_candidates = df[df['Status'].str.lower() == 'hired']

    for idx, row in hired_candidates.iterrows():
        st.markdown(f"### Candidate: {row['Name']} ({row['Email']})")

        role = st.text_input(f"Role for {row['Name']}", key=f"role_{idx}")
        salary = st.text_input(f"Salary for {row['Name']}", key=f"salary_{idx}")

        if st.button(f"✉️ Send Offer Letter to {row['Email']}", key=f"send_offer_{idx}"):
            if not role.strip() or not salary.strip():
                st.error("Please enter Role and Salary before sending the offer letter.")
                continue

            pdf_path = f"offer_letter_{idx}.pdf"
            generate_offer_pdf(row['Name'], role, salary, pdf_path)

            success = send_offer_email_with_pdf(row['Email'], row['Name'], pdf_path)

            if success:
                st.success(f"Offer letter sent to {row['Name']} ({row['Email']}) ✅")
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
            else:
                st.error(f"Failed to send offer letter to {row['Name']} ({row['Email']}).")


if __name__ == "__main__":
    hr_dashboard()
