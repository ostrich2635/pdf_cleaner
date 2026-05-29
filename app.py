import io
import fitz  # PyMuPDF
import streamlit as st

# --- CRITICAL FIX ---
# This line silences the "MuPDF error: format error: cannot find object in xref" 
# warnings that occur when processing poorly formatted PDFs.
fitz.TOOLS.mupdf_display_errors(False)

st.set_page_config(page_title="PDF Text Redactor", layout="centered")
st.title("📄 Custom PDF Text Redactor")
st.write("Upload your PDF files to permanently strip target text and watermarks.")

import os
import shutil
import streamlit as st
import streamlit.components.v1 as components

# --- AUTOMATED PWA INJECTION LOGIC ---
# This block copies your manifest and service worker into Streamlit's actual static frontend directory
try:
    # Locate where Streamlit is installed inside the server/container
    streamlit_static_path = os.path.join(os.path.dirname(st.__file__), "static")
    
    # Paths to copy files into
    manifest_dest = os.path.join(streamlit_static_path, "manifest.json")
    sw_dest = os.path.join(streamlit_static_path, "sw.js")

    # Only copy if they don't exist yet to protect server performance
    if not os.path.exists(manifest_dest):
        shutil.copy("pwa/manifest.json", manifest_dest)
    if not os.path.exists(sw_dest):
        shutil.copy("pwa/sw.js", sw_dest)
except Exception as e:
    print(f"PWA Injection setup warning: {e}")

# --- HTML/JS Injection to trigger mobile installation ---
pwa_html = """
<script>
    // 1. Inject Manifest Link into the parent website header
    var link = window.parent.document.createElement('link');
    link.rel = 'manifest';
    link.href = './manifest.json';
    window.parent.document.getElementsByTagName('head')[0].appendChild(link);

    // 2. Register the Service Worker in the parent scope
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('./sw.js')
        .then(function(reg) { console.log('PWA Service Worker Registered Successfully', reg); })
        .catch(function(err) { console.error('PWA Service Worker Failed', err); });
    }
</script>
"""
# Render the script invisibly on your page layout
components.html(pwa_html, height=0, width=0)

# --- Sidebar Configuration ---
st.sidebar.header("Target Text Settings")
st.sidebar.write("Modify the phrases below. Put each target phrase on a **new line**.")

default_targets = (
    "Rankers  Academy  JEE\n"
    "For More Material Join: @JEEAdvanced_2025"
)

user_input = st.sidebar.text_area(
    "Texts to remove:", 
    value=default_targets, 
    height=150
)

TARGET_TEXTS = [line.strip() for line in user_input.split("\n") if line.strip()]

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
        
        modifications_made = False

        for page in doc:
            # Standardize the page's structural code into one single stream
            page.clean_contents()
            xrefs = page.get_contents()

            if not xrefs:
                continue
            
            # Target the unified content stream
            xref = xrefs[0]
            stream = doc.xref_stream(xref)
            
            if stream:
                stream_modified = False
                for target in TARGET_TEXTS:
                    target_bytes = target.encode("utf-8")
                    
                    if target_bytes in stream:
                        # Create an empty space string of the exact same length
                        blank_spaces = b" " * len(target_bytes)
                        # Swap the watermark text with blank spaces in the byte code
                        stream = stream.replace(target_bytes, blank_spaces)
                        stream_modified = True
                        modifications_made = True

                # If modified, push the cleaned code back into the PDF layer
                if stream_modified:
                    doc.update_stream(xref, stream)

        # Save to memory buffer. garbage=4 cleans up unused background layers.
        output_buffer = io.BytesIO()
        doc.save(output_buffer, garbage=4, deflate=True)
        doc.close()

        # Download interface
        col1, col2 = st.columns([3, 1])
        with col1:
            if modifications_made:
                st.success(f"**{uploaded_file.name}** — Cleaned successfully.")
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
