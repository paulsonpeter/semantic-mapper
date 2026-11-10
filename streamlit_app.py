"""Run with: python -m streamlit run streamlit_app.py"""
import streamlit as st
import sqlite3
import os
import cloud_normalizer as normalizer
import fault_store

st.set_page_config(page_title="Aircraft report normalizer", page_icon=":material/flight:", layout="wide")
st.title("Aircraft report normalizer")
st.caption("Turn a maintenance or fault report paragraph into a short fault term, such as WHEEL NOISE.")
try:
    fault_store.initialize()
except sqlite3.Error:
    st.error("Cannot open the local approval database. Check that the data folder is writable.")
    st.stop()

def setting(name, default=""):
    try:
        return st.secrets.get(name, os.environ.get(name, default))
    except FileNotFoundError:
        return os.environ.get(name, default)


model = setting("OPENAI_MODEL", normalizer.MODEL)
api_key = setting("OPENAI_API_KEY")
st.caption("Powered by a cloud language model. No local software is required.")
if not api_key:
    st.info("Cloud setup pending: the app owner needs to add OPENAI_API_KEY in Streamlit Secrets.")


def clear_result():
    st.session_state.pop("fault_normalization", None)


paragraph = st.text_area(
    "Original paragraph", key="paragraph", height=220,
    max_chars=normalizer.MAX_CHARACTERS, on_change=clear_result,
    placeholder="Describe the aircraft fault, when it occurred, and any observed indications or measurements.",
)
if st.button("Normalize paragraph", type="primary", disabled=not paragraph.strip()):
    clear_result()
    try:
        with st.spinner("Normalizing aircraft terminology..."):
            result = normalizer.normalize_report(paragraph, model, api_key=api_key)
        if not isinstance(result, dict) or not isinstance(result.get("normalized_term"), str) or not result["normalized_term"].strip():
            raise ValueError("The model did not return a fault term. Please try normalizing again.")
        st.session_state.fault_normalization = {"original": paragraph, "model": model, **result}
    except ValueError as exc:
        st.error(str(exc))

result = st.session_state.get("fault_normalization")
if result is not None and (not isinstance(result, dict)
                           or not isinstance(result.get("normalized_term"), str)
                           or not result["normalized_term"].strip()
                           or result.get("original") != paragraph
                           or not isinstance(result.get("model"), str)):
    clear_result()
    result = None
    st.info("The previous result was cleared. Click Normalize paragraph to generate a fault term.")
if result:
    st.subheader("Normalized fault term")
    st.text(result["normalized_term"])
    st.caption(f"Generated with {result['model']}. Review that the term matches the reported fault.")
    if st.button("Approve & save", disabled=result.get("saved", False)):
        try:
            added = fault_store.approve(result["original"], result["normalized_term"], result["model"])
            result["saved"] = True
            st.session_state.fault_normalization = result
            st.rerun()
        except (ValueError, sqlite3.Error):
            st.error("Could not save the approved fault. Please try again.")
    if result.get("saved"):
        st.success("Approved fault saved in the local database.")

st.divider()
st.subheader("Approved faults")
try:
    saved = fault_store.records()
    if saved:
        st.dataframe(saved, hide_index=True,
                     column_order=["paragraph", "normalized_term", "model", "approved_at"],
                     width="stretch", alt="Approved aircraft fault reports and normalized terms")
    else:
        st.info("Approved paragraphs and fault terms will appear here.")
except sqlite3.Error:
    st.error("Could not load approved faults.")
st.caption("Only approved results are saved. Identical paragraph and term pairs are stored once.")
