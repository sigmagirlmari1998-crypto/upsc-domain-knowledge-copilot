
import streamlit as st
from backend.auth import signup, login, current_user


def _set_token(token: str):
    st.session_state["jwt_token"] = token


def render_auth_gate():
    """Returns the authenticated user dict, or None (and renders forms)."""
    user = current_user(st.session_state.get("jwt_token"))
    if user:
        return user

    st.title("🔐 UPSC Co-Pilot — Sign in")
    tab_login, tab_signup = st.tabs(["Login", "Sign up"])

    with tab_login:
        with st.form("login_form"):
            u = st.text_input("Username or email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                try:
                    _set_token(login(u, p))
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    with tab_signup:
        with st.form("signup_form"):
            un = st.text_input("Username", key="su_user")
            em = st.text_input("Email", key="su_email")
            pw = st.text_input("Password (min 6 chars)",
                               type="password", key="su_pw")
            if st.form_submit_button("Create account"):
                try:
                    _set_token(signup(un, em, pw))
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    return None


def render_logout(user):
    st.sidebar.markdown(f"👤 **{user['username']}**")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.pop("jwt_token", None)
        st.session_state.pop("active_corpus_id", None)
        st.rerun()
