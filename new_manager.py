import streamlit as st
import boto3
import pandas as pd
from urllib.parse import urlencode
import plotly.express as px
from streamlit_cognito_auth import CognitoAuthenticator

# Initialize DynamoDB tables
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
resume_table = dynamodb.Table('Resume_Matches')



st.set_page_config(page_title="Manager Dashboard", layout="wide")

st.markdown("""
<style>
/* ===== GENERAL APP STYLING ===== */
.stApp {
    background: linear-gradient(135deg, #e6f2f1, #c6ded9);
    font-family: 'Segoe UI', sans-serif;
    color: #2f4f4f;
}

/* Headings */
h1, h2, h3 {
    color: #2f4f4f;
    font-weight: 700;
}

/* ===== SIDEBAR ===== */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #2e4d4d, #5a7a7a);
    padding: 1rem;
}
[data-testid="stSidebar"] * {
    color: #d9f0f0 !important;
}
[data-testid="stSidebar"] h1, 
[data-testid="stSidebar"] h2, 
[data-testid="stSidebar"] h3 {
    color: #d9f0f0 !important;
}

/* ===== BADGES ===== */
.badge {
    display: inline-block;
    padding: 0.35em 0.8em;
    font-size: 0.85em;
    font-weight: bold;
    border-radius: 12px;
    color: white;
    margin-right: 5px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.15);
}
.badge-strong { background-color: #4caf50; }       /* Green */
.badge-moderate { background-color: #ff9800; }    /* Orange */
.badge-weak { background-color: #f44336; }        /* Red */
.badge-approved { background-color: #9c27b0; }    /* Purple */

/* ===== TABLE ===== */
table {
    border-collapse: collapse;
    width: 100%;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}
thead {
    background-color: #2e4d4d;
    color: #d9f0f0;
    font-weight: 600;
}
tbody tr:nth-child(even) { background-color: #f4f4f4; }
tbody tr:hover { background-color: #c8e6e4; transition: background-color 0.2s ease; }

/* ===== KPI METRICS ===== */
[data-testid="stMetricValue"] {
    color: #2f4f4f;
    font-weight: bold;
}

/* ===== BUTTONS ===== */
.stButton button {
    background: linear-gradient(90deg, #4ca69a, #36827f);
    color: white;
    border-radius: 8px;
    padding: 0.5em 1.2em;
    font-weight: 600;
    border: none;
    transition: all 0.2s ease-in-out;
}
.stButton button:hover {
    background: linear-gradient(90deg, #3b7a78, #2a5e5d);
    transform: scale(1.02);
}

/* ===== EXPANDER HEADERS ===== */
.streamlit-expanderHeader {
    background-color: #d1e6e4;
    padding: 0.6em;
    border-radius: 6px;
    font-weight: 600;
    color: #2f4f4f;
}

/* ===== LINKS ===== */
a {
    color: #3d6c6a;
    text-decoration: none;
    font-weight: 600;
}
a:hover {
    text-decoration: underline;
    color: #4ca69a;
}
</style>
""", unsafe_allow_html=True)



@st.cache_data(ttl=60)
def fetch_candidates():
    response = resume_table.scan()
    return response['Items']

def update_candidate_status(resume_id, jd_id, status, comments):
    try:
        # Use the main 'resume_table', not 'status_table'
        resume_table.update_item(
            Key={
                'ResumeID': resume_id, # Use the correct key names
                'JDID': jd_id
            },
            # This expression updates the 'Status' and 'ManagerNotes' attributes
            UpdateExpression="SET #st = :status, #mc = :comments",
            ExpressionAttributeNames={
                "#st": "Status",
                "#mc": "ManagerNotes"
            },
            ExpressionAttributeValues={
                ":status": status,
                ":comments": comments
            }
        )
        return True # Return True on success
    except Exception as e:
        st.error(f"Error updating candidate: {e}")
        return False # Return False on failure

def get_badge_html(rec):
    rec_lower = rec.lower() if rec else ''
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

def generate_resume_link(url):
    if url and url.strip():
        return f'<a href="{url}" target="_blank">📄 Download</a>'
    else:
        return "No Resume"

def generate_interview_link(name, email):
    base_url = "https://calendly.com/aalapsk07/30min"
    params = urlencode({'name': name, 'email': email})
    full_url = f"{base_url}?{params}"
    return f'<a href="{full_url}" target="_blank">📅 Schedule</a>'

def manager_dashboard():

    st.sidebar.header("Controls")
    if st.sidebar.button("Refresh Data"):
        fetch_candidates.clear()
        if hasattr(st, 'experimental_rerun'):
            st.experimental_rerun()
        else:
            st.sidebar.info("Please manually refresh the page.")

    st.title("🧑‍💼 Manager Dashboard - Shortlisted Candidates")

    candidates = fetch_candidates()

    if not candidates:
        st.warning("No candidates found in ResumeMatches.")
        return

    df = pd.DataFrame(candidates)
    df['Score'] = pd.to_numeric(df['Score'], errors='coerce').fillna(0)


    # Fix missing columns
    if 'Status' not in df.columns:
        df['Status'] = 'Pending'
    if 'ManagerComments' not in df.columns:
        df['ManagerComments'] = ''
    else:
        df['ManagerComments'] = df['ManagerComments'].fillna('')

    df['Status'] = df['Status'].fillna('Pending')

    st.sidebar.header("🔍 Filters")
    min_score, max_score = st.sidebar.slider("Score Range", 0, 100, (0, 100))
    exp_filter = st.sidebar.text_input("Experience Match filter (comma separated)", "")
    skill_filter = st.sidebar.text_input("Skills Match filter (comma separated)", "")

    if exp_filter:
        exp_list = [x.strip().lower() for x in exp_filter.split(",")]
        df = df[df['ExpMatch'].str.lower().apply(lambda x: any(e in x for e in exp_list) if isinstance(x, str) else False)]
    if skill_filter:
        skill_list = [x.strip().lower() for x in skill_filter.split(",")]
        df = df[df['SkillsMatch'].str.lower().apply(lambda x: any(s in x for s in skill_list) if isinstance(x, str) else False)]

    df = df[(df['Score'] >= min_score) & (df['Score'] <= max_score)]

    if df.empty:
        st.info("No candidates found matching current filters.")
        return

    st.sidebar.subheader("Sort By")
    sort_cols = st.sidebar.multiselect("Select columns to sort by", options=['Score', 'ExpMatch', 'SkillsMatch'], default=['Score'])
    ascending = st.sidebar.checkbox("Sort ascending?", value=False)

    if sort_cols:
        df = df.sort_values(by=sort_cols, ascending=ascending)

    df['Shortlisted'] = df['Score'].apply(lambda x: 'Yes' if x >= 70 else 'No')

    st.subheader(f"Candidates ({len(df)})")
    st.dataframe(
        df[['Name', 'Email', 'JDID', 'Score', 'ExpMatch', 'SkillsMatch', 'Shortlisted']].reset_index(drop=True),
        use_container_width=True,
        height=350
    )

    st.subheader("Candidate Comparison Tool")
    name_to_email = dict(zip(df['Name'], df['Email']))
    selected_names = st.multiselect(
        "Select candidates to compare (up to 3)", 
        options=df['Name'].tolist(),
        max_selections=3
    )
    selected_emails = [name_to_email[name] for name in selected_names]

    if selected_emails:
        comp_df = df[df['Email'].isin(selected_emails)][
            ['Name', 'Email', 'JDID', 'Score', 'ExpMatch', 'SkillsMatch', 'Recommendation', 'ManagerComments']
        ].reset_index(drop=True)
        st.dataframe(comp_df.T, use_container_width=True)

    st.subheader("Candidate Details & Status Update")
    for idx, row in df.iterrows():
        with st.expander(f"{row['Name']} - Score: {row['Score']} - Status: {row['Status']}"):
            st.markdown(f"**Email:** {row['Email']}")
            st.markdown(f"**Job ID:** {row['JDID']}")
            st.markdown(f"**Experience Match:** {row['ExpMatch']}")
            st.markdown(f"**Skills Match:** {row['SkillsMatch']}")
            st.markdown(f"**Recommendation:** {row.get('Recommendation', 'N/A')}")
            st.markdown(f"**Summary:** {row.get('Summary', 'No summary available')}")
            st.markdown(f"**Resume:** {generate_resume_link(row.get('ResumeURL', ''))}", unsafe_allow_html=True)
            st.markdown(
                f"**Interview Scheduling:** {generate_interview_link(row['Name'], row['Email'])}",
                unsafe_allow_html=True
            )

            status_options = ['Pending', 'Reviewed', 'Interview Scheduled', 'Rejected', 'Hired']
            current_status = row['Status']
            status = st.selectbox(
                "Update Status",
                options=status_options,
                index=status_options.index(current_status) if current_status in status_options else 0,
                key=f"status_{idx}"
            )

            comments = st.text_area("Manager Comments", value=row['ManagerComments'], key=f"comments_{idx}")

            if st.button("Save Update", key=f"save_{idx}"):
                if update_candidate_status(row['ResumeID'], row['JDID'], status, comments):
                    st.success("Status and comments saved!")
                    fetch_candidates.clear()
                    st.sidebar.info("Data updated! Please click 'Refresh Data' to reload.")
                else:
                    st.error("Failed to save updates.")

    # Charts at the bottom
    st.subheader("Candidate Insights")
    col1, col2 = st.columns(2)

    rec_color_map = {
        'Strong': '#388E3C',
        'Moderate': '#FB8C00',
        'Weak': '#E53935',
        'Approved': '#7E57C2'
    }

    with col1:
        rec_counts = df['Recommendation'].value_counts()
        fig_rec = px.bar(
            x=rec_counts.index,
            y=rec_counts.values,
            labels={'x': 'Recommendation', 'y': 'Count'},
            title="Recommendation Overview",
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

if __name__ == "__main__":
    manager_dashboard()
