import io
import fitz  # PyMuPDF
import streamlit as st
import os
import shutil
import zipfile
import streamlit.components.v1 as components

# --- CRITICAL FIX ---
# This line silences the "MuPDF error: format error: cannot find object in xref" 
# warnings that occur when processing poorly formatted PDFs.
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
except Exception as e:
    print(f"PWA Injection setup warning: {e}")

pwa_html = """
<script>
    var link = window.parent.document.createElement('link');
    link.rel = 'manifest';
    link.href = './manifest.json';
    window.parent.document.getElementsByTagName('head')[0].appendChild(link);

    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('./sw.js')
        .then(function(reg) { console.log('PWA Service Worker Registered Successfully', reg); })
        .catch(function(err) { console.error('PWA Service Worker Failed', err); });
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
            if not f.endswith('/'):
                z_contents[f] = z.read(f)
    return z_contents

def build_tree(paths):
    tree = {}
    for path in paths:
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
                st.checkbox(f"📄 {key} (Will be copied as-is)", key=file_key)


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
            file_paths = list(zip_contents.keys())
            zip_id = uploaded_file.file_id
            
            tree = build_tree(file_paths)
            
            st.write("**Select files to include in the output ZIP. PDFs will be processed automatically.**")
            render_tree(tree, zip_id)

            btn_col, dl_col = st.columns([1, 1])
            
            with btn_col:
                process_clicked = st.button(f"⚙️ Process ZIP", key=f"btn_proc_{zip_id}")

            if process_clicked:
                st.session_state[f"processed_data_{zip_id}"] = None 
                with st.spinner("Cleaning PDFs and rebuilding ZIP..."):
                    output_zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(output_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as out_zip:
                        for path, content in zip_contents.items():
                            file_key = f"file_{zip_id}_{path}"
                            
                            # Only include files that remain checked in the tree
                            if st.session_state.get(file_key, True):
                                if path.lower().endswith('.pdf'):
                                    doc = fitz.open(stream=content, filetype="pdf")
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
                                    # Copy non-PDFs as-is
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
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            modifications_made = False

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
