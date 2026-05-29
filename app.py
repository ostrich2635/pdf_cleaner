import io
import fitz  # PyMuPDF
import streamlit as st

st.set_page_config(page_title="PDF Text Redactor", layout="centered")
st.title("📄 Custom PDF Text Redactor")
st.write("Upload your PDF files to permanently strip target text and watermarks.")

# --- Sidebar Configuration ---
st.sidebar.header("Target Text Settings")
st.sidebar.write("Modify the phrases below. Put each target phrase on a **new line**.")

# Default phrases preset into the text area
default_targets = (
    "Rankers  Academy  JEE\n"
    "For More Material Join: @JEEAdvanced_2025"
)

# Text area layout for user input
user_input = st.sidebar.text_area(
    "Texts to remove:", 
    value=default_targets, 
    height=150
)

# Split the input by lines and filter out empty inputs
TARGET_TEXTS = [line.strip() for line in user_input.split("\n") if line.strip()]

# Display active targets on main page
if TARGET_TEXTS:
    with st.expander("🔍 Currently actively searching for:", expanded=False):
        for text in TARGET_TEXTS:
            st.code(text)
else:
    st.warning("⚠️ No target text provided. The PDFs will not be altered.")

# --- Main File Uploader ---
uploaded_files = st.file_uploader(
    "Choose PDF files", type=["pdf"], accept_multiple_files=True
)

if uploaded_files and TARGET_TEXTS:
    st.write(f"### Processing {len(uploaded_files)} file(s):")

    for uploaded_file in uploaded_files:
        file_bytes = uploaded_file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        total_instances = 0

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

        output_buffer = io.BytesIO()
        doc.save(output_buffer)
        doc.close()

        # Download interface
        col1, col2 = st.columns([3, 1])
        with col1:
            if total_instances > 0:
                st.success(f"**{uploaded_file.name}** — Cleaned {total_instances} phrases.")
            else:
                st.info(f"**{uploaded_file.name}** — No target phrases found.")
        with col2:
            st.download_button(
                label="📥 Download",
                data=output_buffer.getvalue(),
                file_name=f"cleaned_{uploaded_file.name}",
                mime="application/pdf",
                key=uploaded_file.name,
            )
