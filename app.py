
import streamlit as st

st.set_page_config(
    page_title="Cram Jam",
    page_icon="📚",
    layout="wide",
)

st.title("Cram Jam")
st.subheader("Your academic pressure, made visible.")

st.write(
    "Track your courses, deadlines, and study sessions "
    "to understand where your academic pressure comes from."
)

st.divider()

st.header("Your Semester")
st.info(
    "Your semester dashboard will appear here once "
    "you add your courses and academic tasks."
)
