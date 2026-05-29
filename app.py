import io
import fitz  # PyMuPDF
import streamlit as st

st.set_page_config(page_title="PDF Text Redactor", layout="centered")
st.title("📄 PDF Text Redactor")
st.write("Upload your PDF files, and they will be scrubbed automatically.")

# --- Configuration (Your target strings) ---
TARGET_TEXTS = [
    "Rankers  Academy  JEE",
    "For More Material Join: @JEEAdvanced_2025",
]

# File Uploader component (allows multiple files)
uploaded_files = st.file_uploader(
    "Choose PDF files", type=["pdf"], accept_multiple_files=True
)

if uploaded_files:
    st.write(f"### Processing {len(uploaded_files)} file(s):")

    for uploaded_file in uploaded_files:
        # Read file into memory bytes
        file_bytes = uploaded_file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        total_instances = 0

        # Run the redaction process
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_modified = False

            for target_text in TARGET_TEXTS:
                text_instances = page.search_for(target_text)
                if text_instances:
                    total_instances += len(text_instances)
                    for rect in text_instances:
                        page.add_redact_annot(rect, fill=(1, 1, 1))
                    page_modified = True

            if page_modified:
                page.apply_redactions()

        # Save the edited PDF to a memory buffer instead of the hard drive
        output_buffer = io.BytesIO()
        doc.save(output_buffer)
        doc.close()

        # UI Visuals for the user
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(
                f"**{uploaded_file.name}** — Removed {total_instances} instances."
            )
        with col2:
            st.download_button(
                label="📥 Download",
                data=output_buffer.getvalue(),
                file_name=f"cleaned_{uploaded_file.name}",
                mime="application/pdf",
                key=uploaded_file.name,
            )