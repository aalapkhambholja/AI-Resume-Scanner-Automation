import streamlit as st
import boto3
from botocore.exceptions import ClientError
from streamlit_cognito_auth import CognitoAuthenticator

# rerun function using session_state toggle + experimental_rerun (no query params)
def rerun():
    if "rerun_flag" not in st.session_state:
        st.session_state["rerun_flag"] = False
    st.session_state["rerun_flag"] = not st.session_state["rerun_flag"]
    st.rerun()

# Cognito config (replace with your values)
USER_POOL_ID = "us-east-1_Otc9vKvxS"
CLIENT_ID = "3g1264chnmode7i9hiipsmubp8"
AWS_REGION = "us-east-1"

cognito_client = boto3.client("cognito-idp", region_name=AWS_REGION)

def sign_up(username, password, email):
    try:
        cognito_client.sign_up(
            ClientId=CLIENT_ID,
            Username=username,
            Password=password,
            UserAttributes=[{"Name": "email", "Value": email}],
        )
        return True, "Sign up successful! Check your email for the confirmation code."
    except ClientError as e:
        return False, e.response["Error"]["Message"]

def confirm_sign_up(username, code):
    try:
        cognito_client.confirm_sign_up(
            ClientId=CLIENT_ID,
            Username=username,
            ConfirmationCode=code,
        )
        return True, "Confirmation successful! You can now log in."
    except ClientError as e:
        return False, e.response["Error"]["Message"]

def add_user_to_group(username, group_name):
    try:
        cognito_client.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=username,
            GroupName=group_name
        )
        return True, f"User added to group '{group_name}' successfully."
    except ClientError as e:
        return False, e.response["Error"]["Message"]

def sign_in(username, password):
    try:
        response = cognito_client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": username, "PASSWORD": password},
        )
        access_token = response["AuthenticationResult"]["AccessToken"]
        return True, access_token
    except ClientError as e:
        return False, e.response["Error"]["Message"]

def get_user_groups(username):
    try:
        response = cognito_client.admin_list_groups_for_user(
            Username=username,
            UserPoolId=USER_POOL_ID,
        )
        return [group["GroupName"] for group in response["Groups"]]
    except ClientError as e:
        st.error(f"Failed to get user groups: {e.response['Error']['Message']}")
        return []

def get_username_from_token(access_token):
    try:
        response = cognito_client.get_user(AccessToken=access_token)
        return response["Username"]
    except ClientError as e:
        st.error(f"Failed to get user info: {e.response['Error']['Message']}")
        return None

# Initialize session state variables
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_groups" not in st.session_state:
    st.session_state.user_groups = []
if "pending_user" not in st.session_state:
    st.session_state.pending_user = None
if "pending_role" not in st.session_state:
    st.session_state.pending_role = None

st.title("HR/Manager Login Portal")

menu = ["Sign Up", "Confirm Sign Up", "Sign In"]
choice = st.sidebar.selectbox("Choose Action", menu)

if choice == "Sign Up":
    st.subheader("Create a new account")
    username = st.text_input("Username", key="signup_username")
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_password")
    role = st.selectbox("Select Role", ["HR", "Manager"], key="signup_role")
    if st.button("Sign Up"):
        if not username or not email or not password:
            st.error("Please fill in all fields")
        else:
            success, msg = sign_up(username, password, email)
            if success:
                st.success(msg)
                st.session_state.pending_user = username
                st.session_state.pending_role = role
            else:
                st.error(msg)

elif choice == "Confirm Sign Up":
    st.subheader("Confirm your account")
    username = st.text_input("Username", value=st.session_state.pending_user or "", key="confirm_username")
    code = st.text_input("Confirmation Code", key="confirm_code")
    if st.button("Confirm"):
        if not username or not code:
            st.error("Please enter username and confirmation code")
        else:
            success, msg = confirm_sign_up(username, code)
            if success:
                st.success(msg)
                role = st.session_state.pending_role
                if role:
                    added, msg2 = add_user_to_group(username, role)
                    if added:
                        st.success(msg2)
                    else:
                        st.error(msg2)
                else:
                    st.warning("Role not found in session. Please contact admin.")
                st.session_state.pending_user = None
                st.session_state.pending_role = None
            else:
                st.error(msg)

elif choice == "Sign In":
    if not st.session_state.logged_in:
        st.subheader("Login to your account")
        username = st.text_input("Username", key="signin_username")
        password = st.text_input("Password", type="password", key="signin_password")
        if st.button("Sign In"):
            if not username or not password:
                st.error("Please enter username and password")
            else:
                success, access_token_or_msg = sign_in(username, password)
                if success:
                    access_token = access_token_or_msg
                    user_name = get_username_from_token(access_token)
                    if user_name:
                        groups = get_user_groups(user_name)
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.user_groups = [g.lower() for g in groups]
                        rerun()
                    else:
                        st.error("Could not retrieve user info.")
                else:
                    st.error(access_token_or_msg)
    else:
        st.write(f"Welcome, **{st.session_state.username}**!")
        st.write(f"Your groups: {st.session_state.user_groups}")

        if "hr" in st.session_state.user_groups:
            st.success("You are an HR user.")
            st.markdown("[Go to HR Dashboard](http://localhost:8502)", unsafe_allow_html=True)
        elif "manager" in st.session_state.user_groups:
            st.success("You are a Manager user.")
            st.markdown("[Go to Manager Dashboard](http://localhost:8503)", unsafe_allow_html=True)
        else:
            st.warning("No dashboard assigned to your user group.")

        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.user_groups = []
            rerun()
