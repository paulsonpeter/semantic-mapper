"""Run with: python -m streamlit run streamlit_app.py"""
import sqlite3
import streamlit as st
import mapper

st.set_page_config(page_title="Semantic mapper", page_icon=":material/hub:", layout="wide")
st.title("Semantic mapper")
st.caption("Different expressions. Consistent concepts. Your mappings stay in your local database.")
mapper.initialize()
if message := st.session_state.pop("notice", None):
    st.success(message)


def done(message):
    st.session_state.notice = message
    st.rerun()


with st.sidebar:
    st.subheader("Workspace")
    page = st.radio("Navigate", ["Test phrases", "Manage mappings", "Manage concepts", "Import / export"], label_visibility="collapsed")
    st.divider()
    st.metric("Concepts", len(mapper.concepts()))
    st.metric("Mapped phrases", len(mapper.mappings()))
    st.caption("Explicit matching · No AI calls")

try:
    if page == "Test phrases":
        st.subheader("Test your phrases")
        st.caption("Enter one phrase or a batch, one per line. Case, punctuation and extra spaces are ignored. Words are not reordered or guessed.")
        with st.form("test"):
            text = st.text_area("Phrases", value="Sound from wheel!\nrattling from tyre\nunknown sound", height=160)
            submitted = st.form_submit_button("Match phrases", type="primary")
        if submitted:
            phrases = [line.strip() for line in text.splitlines() if line.strip()]
            if not phrases:
                st.warning("Enter at least one phrase.")
            else:
                results = mapper.match(phrases)
                st.dataframe(results, hide_index=True, width="stretch", alt="Phrase matching results")
                matched = sum(r["status"] == "Matched" for r in results)
                st.caption(f"{matched} matched · {len(results) - matched} unmapped")
                if len(results) == 1:
                    st.json({"concept": results[0]["concept"], "detail": results[0]["detail"]})

    elif page == "Manage concepts":
        st.subheader("Manage concepts")
        st.caption("Concepts are standard labels, such as WHEEL_NOISE. Optional details use the same label format.")
        with st.form("concept"):
            name = st.text_input("New concept", placeholder="BRAKE_NOISE")
            if st.form_submit_button("Add concept", type="primary"):
                mapper.add_concept(name)
                done("Concept added.")
        names = mapper.concepts()
        st.dataframe([{"concept": n} for n in names], hide_index=True, alt="Available concepts")
        if names:
            with st.expander("Delete a concept"):
                selected = st.selectbox("Concept to delete", names)
                confirmed = st.checkbox("Delete this concept")
                if st.button("Delete concept", disabled=not confirmed):
                    mapper.delete_concept(selected)
                    done("Concept deleted.")

    elif page == "Manage mappings":
        st.subheader("Manage mappings")
        rows = mapper.mappings()
        search = st.text_input("Filter mappings", placeholder="Search phrase, concept or detail")
        filtered = [r for r in rows if search.casefold() in " ".join(str(v) for v in r.values()).casefold()]
        st.dataframe(filtered, hide_index=True, column_order=["phrase", "concept", "detail"], alt="Saved phrase mappings")
        names = mapper.concepts()
        if not names:
            st.info("Add a concept first in Manage concepts.")
        else:
            selected_id = st.selectbox("Add or edit", [None] + [r["id"] for r in rows],
                                       format_func=lambda i: "New mapping" if i is None else next(r["phrase"] for r in rows if r["id"] == i))
            current = next((r for r in rows if r["id"] == selected_id), {})
            with st.form(f"mapping_{selected_id}"):
                phrase = st.text_input("Phrase", value=current.get("phrase", ""))
                concept = st.selectbox("Concept", names, index=names.index(current["concept"]) if current else 0)
                detail = st.text_input("Optional detail", value=current.get("detail", ""), placeholder="RATTLING")
                if st.form_submit_button("Save mapping", type="primary"):
                    mapper.save_mapping(phrase, concept, detail, selected_id)
                    done("Mapping saved.")
            if selected_id is not None:
                confirmed = st.checkbox("Delete this mapping", key=f"delete_{selected_id}")
                if st.button("Delete mapping", disabled=not confirmed):
                    mapper.delete_mapping(selected_id)
                    done("Mapping deleted.")

    else:
        st.subheader("Import / export")
        st.caption("CSV columns: phrase,concept,detail. Import adds new phrases and concepts, skips identical mappings, and rejects conflicts. A failed import saves nothing.")
        st.download_button("Export mappings", mapper.export_csv(mapper.mappings()), "semantic_mappings.csv", "text/csv")
        st.code("phrase,concept,detail\nrattling from tyre,WHEEL_NOISE,RATTLING", language="csv")
        with st.form("import"):
            upload = st.file_uploader("Choose a UTF-8 CSV file", type="csv")
            if st.form_submit_button("Import mappings", type="primary"):
                if upload is None:
                    st.warning("Choose a CSV file first.")
                else:
                    count = mapper.import_csv(upload.getvalue().decode("utf-8-sig"))
                    done(f"Imported {count} new mappings.")
except sqlite3.IntegrityError:
    st.error("This phrase or concept already exists, or its concept is no longer available. Normalized phrases must be unique.")
except (ValueError, UnicodeError) as exc:
    st.error(str(exc))
