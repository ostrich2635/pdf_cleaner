import io
import fitz  # PyMuPDF
import streamlit as st
import os
import shutil
import zipfile
import streamlit.components.v1 as components

# --- CRITICAL FIX ---
fitz.TOOLS.mupdf_display_errors(False)

st.set_page_config(page_title="PDF Text Redactor", layout="centered")
st.title("📄 Custom PDF Text Redactor")
st.write("Upload your PDF or ZIP files to permanently strip target text and watermarks.")

# --- AUTOMATED PWA INJECTION LOGIC ---
try:
    streamlit_static_path = os.path.join(os.path.dirname(st.__file__), "static")
    manifest_dest = os.path.join(streamlit_static_path, "manifest.json")
    sw_dest = os.path.join(streamlit_static_path, "sw.js")

    if not os.path.exists(manifest_dest):
        shutil.copy("pwa/manifest.json", manifest_dest)
    if not os.path.exists(sw_dest):
        shutil.copy("pwa/sw.js", sw_dest)
except Exception:
    pass

pwa_html = """
<script>
    var link = window.parent.document.createElement('link');
    link.rel = 'manifest';
    link.href = './manifest.json';
    window.parent.document.getElementsByTagName('head')[0].appendChild(link);

    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('./sw.js')
    }
</script>
"""
components.html(pwa_html, height=0, width=0)

# --- Sidebar Configuration ---
st.sidebar.header("Target Text Settings")
st.sidebar.write("Modify the phrases below. Put each target phrase on a **new line**.")

default_targets = (
    "Rankers  Academy  JEE\n"
    "For More Material Join: @JEEAdvanced_2025\n"
    "For More Join: @IITJEE_Advanced\n"
    "For More Material Join: @JEEAdvanced_2024"
)

user_input = st.sidebar.text_area("Texts to remove:", value=default_targets, height=150)
TARGET_TEXTS = [line.strip() for line in user_input.split("\n") if line.strip()]

if TARGET_TEXTS:
    with st.expander("🔍 Currently actively searching for:", expanded=False):
        for text in TARGET_TEXTS:
            st.code(text)
else:
    st.warning("⚠️ No target text provided. The PDFs will not be altered.")

# --- ZIP Helper Functions ---
@st.cache_data
def parse_zip(f_bytes):
    z_contents = {}
    with zipfile.ZipFile(io.BytesIO(f_bytes)) as z:
        for f in z.namelist():
            z_contents[f] = z.read(f)
    return z_contents

def build_tree(paths):
    tree = {}
    for path in paths:
        if path.endswith('/'):
            continue  # Skip raw directory markers for the visual tree
        parts = path.split('/')
        curr = tree
        for part in parts[:-1]:
            if part not in curr:
                curr[part] = {}
            curr = curr[part]
        curr[parts[-1]] = path
    return tree

def get_all_files(node):
    files = []
    for k, v in node.items():
        if isinstance(v, dict):
            files.extend(get_all_files(v))
        else:
            files.append(v)
    return files

def toggle_folder(folder_key, child_files, z_id):
    state = st.session_state[folder_key]
    for f in child_files:
        st.session_state[f"file_{z_id}_{f}"] = state

def render_tree(node, z_id, current_path=""):
    for key, val in node.items():
        if isinstance(val, dict):
            folder_path = f"{current_path}/{key}" if current_path else key
            with st.expander(f"📁 {key}", expanded=True):
                all_children = get_all_files(val)
                folder_key = f"folder_{z_id}_{folder_path}"
                
                if folder_key not in st.session_state:
                    st.session_state[folder_key] = True

                st.checkbox(
                    f"Select all in {key}", 
                    key=folder_key, 
                    on_change=toggle_folder, 
                    args=(folder_key, all_children, z_id)
                )
                render_tree(val, z_id, folder_path)
        else:
            file_key = f"file_{z_id}_{val}"
            if file_key not in st.session_state:
                st.session_state[file_key] = True
            
            if val.lower().endswith('.pdf'):
                st.checkbox(f"📄 {key}", key=file_key)
            else:
                st.checkbox(f"📄 {key} (Will be copied as-is)", key=file_key, disabled=True)

# --- Main File Uploader ---
uploaded_files = st.file_uploader(
    "Choose PDF or ZIP files", type=["pdf", "zip"], accept_multiple_files=True
)

if uploaded_files and TARGET_TEXTS:
    st.write(f"### Processing {len(uploaded_files)} file(s):")

    for uploaded_file in uploaded_files:
        file_bytes = uploaded_file.read()
        
        # --- ZIP FILE PROCESSING ---
        if uploaded_file.name.lower().endswith('.zip'):
            st.write("---")
            st.write(f"#### 📦 {uploaded_file.name}")
            
            zip_contents = parse_zip(file_bytes)
            zip_id = uploaded_file.file_id
            tree = build_tree(zip_contents.keys())
            
            st.write("**Select the PDFs you want to redact. Unchecked PDFs and all non-PDF files will be included in the output ZIP exactly as they are.**")
            render_tree(tree, zip_id)

            btn_col, dl_col = st.columns([1, 1])
            
            with btn_col:
                process_clicked = st.button(f"⚙️ Process ZIP", key=f"btn_proc_{zip_id}")

            if process_clicked:
                st.session_state[f"processed_data_{zip_id}"] = None 
                with st.spinner("Processing files and rebuilding ZIP..."):
                    output_zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(output_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as out_zip:
                        for path, content in zip_contents.items():
                            
                            # Write directory structures exactly as they were
                            if path.endswith('/'):
                                out_zip.writestr(path, content)
                                continue

                            file_key = f"file_{zip_id}_{path}"
                            is_checked = st.session_state.get(file_key, True)
                            
                            # Redact only if checked AND it is a PDF
                            if is_checked and path.lower().endswith('.pdf'):
                                try:
                                    doc = fitz.open(stream=content, filetype="pdf")
                                    # Prevent crash on empty/corrupted 0-page PDFs
                                    if doc.page_count > 0:
                                        for page in doc:
                                            page.clean_contents()
                                            xrefs = page.get_contents()
                                            if not xrefs:
                                                continue
                                            xref = xrefs[0]
                                            stream = doc.xref_stream(xref)
                                            if stream:
                                                stream_modified = False
                                                for target in TARGET_TEXTS:
                                                    target_bytes = target.encode("utf-8")
                                                    if target_bytes in stream:
                                                        blank_spaces = b" " * len(target_bytes)
                                                        stream = stream.replace(target_bytes, blank_spaces)
                                                        stream_modified = True
                                                if stream_modified:
                                                    doc.update_stream(xref, stream)
                                        
                                        out_pdf_buffer = io.BytesIO()
                                        doc.save(out_pdf_buffer, garbage=4, deflate=True)
                                        doc.close()
                                        out_zip.writestr(path, out_pdf_buffer.getvalue())
                                    else:
                                        # If it's a 0-page PDF, skip redaction and copy as-is
                                        doc.close()
                                        out_zip.writestr(path, content)
                                except Exception:
                                    # If PyMuPDF fails entirely to read it, copy as-is
                                    out_zip.writestr(path, content)
                            else:
                                # Copy un-checked PDFs and non-PDFs to output as-is
                                out_zip.writestr(path, content)
                                
                    st.session_state[f"processed_data_{zip_id}"] = output_zip_buffer.getvalue()
                    
            if st.session_state.get(f"processed_data_{zip_id}"):
                with dl_col:
                    st.download_button(
                        label=f"📥 Download Processed ZIP",
                        data=st.session_state[f"processed_data_{zip_id}"],
                        file_name=f"cleaned_{uploaded_file.name}",
                        mime="application/zip",
                        key=f"dl_{zip_id}",
                    )

        # --- ORIGINAL PDF PROCESSING ---
        elif uploaded_file.name.lower().endswith('.pdf'):
            st.write("---")
            try:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                modifications_made = False

                if doc.page_count > 0:
                    for page in doc:
                        page.clean_contents()
                        xrefs = page.get_contents()

                        if not xrefs:
                            continue
                        
                        xref = xrefs[0]
                        stream = doc.xref_stream(xref)
                        
                        if stream:
                            stream_modified = False
                            for target in TARGET_TEXTS:
                                target_bytes = target.encode("utf-8")
                                
                                if target_bytes in stream:
                                    blank_spaces = b" " * len(target_bytes)
                                    stream = stream.replace(target_bytes, blank_spaces)
                                    stream_modified = True
                                    modifications_made = True

                            if stream_modified:
                                doc.update_stream(xref, stream)

                    output_buffer = io.BytesIO()
                    doc.save(output_buffer, garbage=4, deflate=True)
                    doc.close()

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
                else:
                    doc.close()
                    st.error(f"**{uploaded_file.name}** contains 0 pages and cannot be processed.")
            except Exception as e:
                st.error(f"Failed to process **{uploaded_file.name}**. It may be corrupted. Error: {e}")
