import streamlit as st
import requests
import io

# Set page configuration for better appearance
st.set_page_config(page_title="LanguageTool Grammar Checker", layout="wide")

# Custom CSS for styling
st.markdown("""
    <style>
    .main-container { padding: 1rem; }
    .highlighted-text { font-size: 1.1rem; line-height: 1.6; }
    .error-highlight-grammar { background-color: #fef2f2; border-bottom: 2px solid #dc2626; padding: 0 2px; position: relative; }
    .error-highlight-spelling { background-color: #fff3cd; border-bottom: 2px solid #ffca28; padding: 0 2px; position: relative; }
    .error-highlight:hover .tooltip { visibility: visible; opacity: 1; }
    .tooltip { visibility: hidden; width: 200px; background-color: #333; color: #fff; text-align: center; border-radius: 6px; padding: 5px; position: absolute; z-index: 1; bottom: 125%; left: 50%; margin-left: -100px; opacity: 0; transition: opacity 0.3s; }
    .suggestions-box { background-color: #f9fafb; padding: 1rem; border-radius: 8px; margin-top: 1rem; }
    .dark-mode .suggestions-box { background-color: #374151; }
    .copy-btn { background-color: #2563eb; color: white; border: none; padding: 0.5em 1em; border-radius: 4px; cursor: pointer; font-size: 1em; margin-bottom: 1em; }
    .dark-mode { background-color: #111827; color: #e5e7eb; }
    .ignore-btn { background-color: #6b7280; color: white; border: none; padding: 0.25em 0.75em; border-radius: 4px; cursor: pointer; font-size: 0.9em; margin-left: 0.5em; }
    .dark-mode .ignore-btn { background-color: #4b5563; }
    </style>
""", unsafe_allow_html=True)

# Dark mode toggle
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

if st.sidebar.button("Toggle Dark Mode"):
    st.session_state.dark_mode = not st.session_state.dark_mode
    st.rerun()

# Apply dark mode class if enabled
if st.session_state.dark_mode:
    st.markdown('<div class="dark-mode">', unsafe_allow_html=True)

# Set page title
st.title("LanguageTool Grammar Checker")

# Sidebar for options
st.sidebar.header("Options")
language = st.sidebar.selectbox("Language", ["en-US", "de-DE", "fr-FR", "es-ES", "auto"], index=0)
picky_mode = st.sidebar.checkbox("Picky Mode")
filter_minor = st.sidebar.checkbox("Filter Minor Issues")

# Default text
default_text = """Dear Recruitment Team,

I am writting  to apply for the position of Senior Analyst at your company. My name is Alex Joness, and I have over five years of experience in data analysis and project managment. I beleive my skills make me a strong candidate for this role.

I currently works as a Data Analyst at TechCorp, where I has developed expertise in SQL, Python, and data visualisation. One of my key achievements was leading a project that improved data processing times by  30%. I also have experience working with cross-functional teams to deliver insights that drives business decisions.

In my previous role at Innovate Ltd, I was responsible for managing a team of three analysts. We was tasked with analyzing customer feedback and presenting findings to senior management. During this time, I learned the importance of clear communication and attention to detail, which I applies to all my work.

I am excited about the opportunity to contribute to your team and would be greatful for the chance to discuss my qualifications further. Please find my resume attached for your review. I looks forward to hearing from you.

Sincerely,  
Alex Joness  
alex.joness@email.com  
+1-555-123-4567"""

# Initialize session state
if "current_text" not in st.session_state:
    st.session_state.current_text = default_text
if "matches" not in st.session_state:
    st.session_state.matches = []
if "filtered_matches" not in st.session_state:
    st.session_state.filtered_matches = []
if "checked" not in st.session_state:
    st.session_state.checked = False
if "ignored_errors" not in st.session_state:
    st.session_state.ignored_errors = set()

# Text input area
input_text = st.text_area(
    "Enter your text here:",
    value=st.session_state.current_text,
    height=300,
    key="main_text_area"
)

# Word and character count
st.write(f"**Word Count**: {len(input_text.split())} | **Character Count**: {len(input_text)}")

# Update session state if user edits text area directly
if input_text != st.session_state.current_text:
    st.session_state.current_text = input_text
    st.session_state.matches = []
    st.session_state.filtered_matches = []
    st.session_state.checked = False
    st.session_state.ignored_errors.clear()

# Function to highlight errors with tooltips
def highlight_errors(text, matches):
    highlighted = text
    matches = sorted(matches, key=lambda x: x["offset"], reverse=True)
    for match in matches:
        if match["offset"] in st.session_state.ignored_errors:
            continue
        start = match["offset"]
        length = match["length"]
        if start >= 0 and start + length <= len(highlighted):
            error_text = highlighted[start:start + length]
            error_type = "spelling" if "typo" in match["message"].lower() else "grammar"
            tooltip = f'<span class="tooltip">{match["message"]}</span>'
            span = f'<span class="error-highlight-{error_type}">{error_text}{tooltip}</span>'
            highlighted = highlighted[:start] + span + highlighted[start + length:]
    return highlighted.replace("\n", "<br>")

# Function to apply a single suggestion
def apply_suggestion(idx):
    match = st.session_state.filtered_matches[idx]
    offset = match["offset"]
    length = match["length"]
    suggestion = match["replacements"][0]["value"] if match["replacements"] else ""
    text = st.session_state.current_text
    new_text = text[:offset] + suggestion + text[offset + length:]
    st.session_state.current_text = new_text
    return new_text

# Function to apply all suggestions
def apply_all_suggestions():
    text = st.session_state.current_text
    for idx in range(len(st.session_state.filtered_matches)):
        match = st.session_state.filtered_matches[idx]
        offset = match["offset"]
        length = match["length"]
        suggestion = match["replacements"][0]["value"] if match["replacements"] else ""
        text = text[:offset] + suggestion + text[offset + length:]
    st.session_state.current_text = text
    # Re-check the text to update matches
    result = check_text(st.session_state.current_text, language, picky_mode)
    st.session_state.matches = result.get("matches", [])
    st.session_state.filtered_matches = [
        m for m in st.session_state.matches
        if m["offset"] not in st.session_state.ignored_errors and
        (not filter_minor or not any(keyword in m["message"].lower() for keyword in ["whitespace", "typo"]))
    ]

# Function to ignore an error
def ignore_error(idx):
    match = st.session_state.filtered_matches[idx]
    st.session_state.ignored_errors.add(match["offset"])
    st.session_state.filtered_matches = [
        m for m in st.session_state.filtered_matches
        if m["offset"] not in st.session_state.ignored_errors
    ]
    st.rerun()

# Cache the API call to avoid redundant requests
@st.cache_data
def check_text(text, language, picky):
    params = {
        "text": text,
        "language": language,
        "picky": "true" if picky else "false"
    }
    response = requests.post("https://api.languagetool.org/v2/check", data=params)
    response.raise_for_status()
    return response.json()

# Check text button
if st.button("Check Text", help="Check the text for grammar and spelling issues"):
    if not st.session_state.current_text.strip():
        st.error("Please enter some text to check.")
    else:
        with st.spinner("Checking..."):
            try:
                result = check_text(st.session_state.current_text, language, picky_mode)
                st.session_state.matches = result.get("matches", [])

                # Filter minor issues if selected and exclude ignored errors
                st.session_state.filtered_matches = [
                    m for m in st.session_state.matches
                    if m["offset"] not in st.session_state.ignored_errors and
                    (not filter_minor or not any(keyword in m["message"].lower() for keyword in ["whitespace", "typo"]))
                ]
                st.session_state.checked = True

            except requests.exceptions.HTTPError as e:
                st.error(f"API Error: {str(e)}. Please try again later.")
                st.session_state.checked = False
            except Exception as e:
                st.error(f"Unexpected Error: {str(e)}. Please check your input or try again.")
                st.session_state.checked = False

# Reset button
if st.button("Reset", help="Clear the text and reset the app"):
    st.session_state.current_text = default_text
    st.session_state.matches = []
    st.session_state.filtered_matches = []
    st.session_state.checked = False
    st.session_state.ignored_errors.clear()
    st.rerun()

# Show results if checked
if st.session_state.checked:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Text with Highlights")
        if not st.session_state.matches:
            st.success("No issues found! Your text looks good.")
            st.markdown(st.session_state.current_text.replace("\n", "<br>"), unsafe_allow_html=True)
        else:
            if not st.session_state.filtered_matches:
                st.success("No major issues found after filtering or all errors ignored.")
                st.markdown(st.session_state.current_text.replace("\n", "<br>"), unsafe_allow_html=True)
            else:
                # Display highlighted text
                highlighted_text = highlight_errors(st.session_state.current_text, st.session_state.filtered_matches)
                st.markdown(f'<div class="highlighted-text">{highlighted_text}</div>', unsafe_allow_html=True)

    with col2:
        if st.session_state.filtered_matches:
            st.subheader("Suggestions")
            # Apply All button
            if st.button("Apply All Suggestions", help="Apply all suggestions at once"):
                apply_all_suggestions()
                st.rerun()

            # Individual suggestions
            for i, match in enumerate(st.session_state.filtered_matches):
                context = match["context"]["text"]
                error_text = context[match["context"]["offset"]:match["context"]["offset"] + match["context"]["length"]]
                suggestion = match["replacements"][0]["value"] if match["replacements"] else None
                st.write(f"**Issue {i+1}**: {match['message']}")
                st.write(f"**Context**: {context}")
                st.write(f"**Error**: {error_text}")
                st.write(f"**Suggestion**: {suggestion if suggestion else 'None'}")
                if suggestion:
                    col_btn = st.columns([3, 1])
                    with col_btn[0]:
                        if st.button(f"Apply Suggestion {i+1}", key=f"apply_{i}", help=f"Apply suggestion: {suggestion}"):
                            apply_suggestion(i)
                            result = check_text(st.session_state.current_text, language, picky_mode)
                            st.session_state.matches = result.get("matches", [])
                            st.session_state.filtered_matches = [
                                m for m in st.session_state.matches
                                if m["offset"] not in st.session_state.ignored_errors and
                                (not filter_minor or not any(keyword in m["message"].lower() for keyword in ["whitespace", "typo"]))
                            ]
                            st.rerun()
                    with col_btn[1]:
                        if st.button("Ignore Error", key=f"ignore_{i}", help="Ignore this error"):
                            ignore_error(i)
                            st.success(f"Ignored error at offset {match['offset']}")
                st.markdown("---")

    # Copy and Export Section
    st.subheader("Export Corrected Text")
    safe_text = st.session_state.current_text.replace("`", "\\`").replace("\\", "\\\\").replace("\n", "\\n")
    copy_html = f"""
    <button class="copy-btn" onclick="navigator.clipboard.writeText(`{safe_text}`)" aria-label="Copy corrected text to clipboard">Copy to Clipboard</button>
    """
    st.markdown(copy_html, unsafe_allow_html=True)

    # Download button
    buffer = io.StringIO()
    buffer.write(st.session_state.current_text)
    st.download_button(
        label="Download Corrected Text",
        data=buffer.getvalue(),
        file_name="corrected_text.txt",
        mime="text/plain",
        help="Download the corrected text as a .txt file"
    )

# Close dark mode div if enabled
if st.session_state.dark_mode:
    st.markdown('</div>', unsafe_allow_html=True)