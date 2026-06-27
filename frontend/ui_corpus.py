import streamlit as st
from backend.corpus_manager import (create_corpus, list_corpora,
                                    delete_corpus, get_active_corpus)


def render_corpus_sidebar(user):
    st.sidebar.header("📚 Active Corpus")
    corpora = list_corpora(user["id"])

    if not corpora:
        st.sidebar.info("No corpora yet. Create one below.")
    else:
        names = [c["name"] for c in corpora]
        ids = [c["id"] for c in corpora]
        current_id = st.session_state.get("active_corpus_id")
        default_idx = ids.index(current_id) if current_id in ids else 0
        choice = st.sidebar.selectbox("Select corpus", names, index=default_idx)
        new_id = ids[names.index(choice)]
        if st.session_state.get("active_corpus_id") != new_id:
            st.session_state["active_corpus_id"] = new_id
            st.rerun()

    with st.sidebar.expander("➕ New Corpus"):
        new_name = st.text_input("Name", key="new_corpus_name")
        if st.button("Create", key="create_corpus_btn"):
            if new_name.strip():
                cid = create_corpus(user["id"], new_name.strip())
                st.session_state["active_corpus_id"] = cid
                st.rerun()

    active_id = st.session_state.get("active_corpus_id")
    if active_id:
        with st.sidebar.expander("🗑️ Delete current corpus"):
            if st.button("Delete permanently", key="del_corpus_btn"):
                delete_corpus(user["id"], active_id)
                st.session_state.pop("active_corpus_id", None)
                st.rerun()

    return get_active_corpus(user["id"], active_id) if active_id else None
