import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv
import time
import re
import streamlit.components.v1 as components

st.set_page_config(
    page_title="GenAI Translator",
    page_icon="🗯️",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_dotenv()

# Get API key from environment variable
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
REFERRER = "http://localhost:8501/" 
APP_NAME = "Simple AI powered Translator"

# Free AI models
AI_MODELS = [
    "google/gemini-2.0-flash-001",
    "google/gemma-3-12b-it"
]

# Function to split text into manageable chunks
def split_text(text, max_chunk_size=1500):
    """
    Split text into chunks of approximately max_chunk_size characters.
    Try to split at paragraph or sentence boundaries when possible.
    """
    # If text is already small enough, return it as is
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    
    # First try to split by paragraphs (double newlines)
    paragraphs = re.split(r'\n\s*\n', text)
    current_chunk = ""
    
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 2 <= max_chunk_size:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
        else:
            # If adding paragraph exceeds limit, check if current chunk exists
            if current_chunk:
                chunks.append(current_chunk)
            
            # If the paragraph itself is too long, split it by sentences
            if len(paragraph) > max_chunk_size:
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                current_chunk = ""
                
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 1 <= max_chunk_size:
                        if current_chunk:
                            current_chunk += " " + sentence
                        else:
                            current_chunk = sentence
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        
                        # If the sentence itself is too long, just split by max_chunk_size
                        if len(sentence) > max_chunk_size:
                            for i in range(0, len(sentence), max_chunk_size):
                                chunks.append(sentence[i:i+max_chunk_size])
                            current_chunk = ""
                        else:
                            current_chunk = sentence
            else:
                current_chunk = paragraph
    
    # Add the last chunk if it exists
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

# Function to translate text
def translate_text(text, source_lang, target_lang, model):
    # For very long texts, split into chunks
    chunks = split_text(text)
    
    if len(chunks) == 1:
        # For single chunk texts, just translate directly
        return translate_single_chunk(chunks[0], source_lang, target_lang, model)
    
    # For multi-chunk texts, process sequentially with progress updates
    translated_chunks = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, chunk in enumerate(chunks):
        status_text.text(f"Translating part {i+1} of {len(chunks)}...")
        
        # Create context-aware prompt based on position
        if i == 0:
            # First chunk
            system_prompt = f"You are a professional translator. Translate the following text from {source_lang} to {target_lang}. This is the BEGINNING of a longer document. Maintain the original formatting and translate everything completely. Only provide the translation, no explanations."
        elif i == len(chunks) - 1:
            # Last chunk
            system_prompt = f"You are a professional translator. Translate the following text from {source_lang} to {target_lang}. This is the FINAL part of a longer document. Maintain coherence with previous parts. Maintain the original formatting and translate everything completely. Only provide the translation, no explanations."
        else:
            # Middle chunk
            system_prompt = f"You are a professional translator. Translate the following text from {source_lang} to {target_lang}. This is a MIDDLE part of a longer document. Maintain coherence with previous parts. Maintain the original formatting and translate everything completely. Only provide the translation, no explanations."
        
        # Add a short delay to prevent API rate limiting
        time.sleep(0.5)
        
        # Translate this chunk
        chunk_result = translate_with_custom_system_prompt(chunk, source_lang, target_lang, model, system_prompt)
        translated_chunks.append(chunk_result)
        
        # Update progress
        progress_bar.progress((i + 1) / len(chunks))
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
    
    # Combine all translated chunks
    return "\n\n".join(translated_chunks)

# Function to translate a single chunk
def translate_single_chunk(text, source_lang, target_lang, model):
    return translate_with_custom_system_prompt(
        text, 
        source_lang, 
        target_lang, 
        model,
        f"You are a professional translator. Translate the following text from {source_lang} to {target_lang}. Maintain the original formatting and translate everything completely. Only provide the translation, no additional explanations."
    )

# Function to translate with a custom system prompt
def translate_with_custom_system_prompt(text, source_lang, target_lang, model, system_prompt):
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": REFERRER,
            "X-Title": APP_NAME,
        },
        data=json.dumps({
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": text
                }
            ]
        })
    )

    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"Error: {response.status_code}, {response.text}"

# Function to create a copy button component
def create_copy_button(text_to_copy, button_id):
    # Use json.dumps to properly escape the text for JavaScript
    escaped_text = json.dumps(text_to_copy if text_to_copy else "")
    copy_js = f"""
    <div style="text-align: right; width: auto;">
    <script>
    function copyTextToClipboard_{button_id}() {{
        navigator.clipboard.writeText({escaped_text})
        .then(() => {{
            const button = document.getElementById('copy_button_{button_id}');
            const originalText = button.innerText;
            button.innerText = 'Copied!';
            setTimeout(() => button.innerText = originalText, 2000);
        }})
        .catch(err => console.error('Error copying text: ', err));
    }}
    </script>
    <button id="copy_button_{button_id}" onclick="copyTextToClipboard_{button_id}()" 
        style="font-family: 'Source Sans', sans-serif;
               font-size: 0.8rem;
               line-height: 1.2;
               display: inline-flex;
               box-sizing: border-box;
               margin: 0px;
               overflow: visible;
               appearance: button;
               align-items: center;
               justify-content: center;
               font-weight: 400;
               padding: 0.25rem 0.75rem;
               border-radius: 0.5rem;
               min-height: 30px;
               text-transform: none;
               color: rgb(49, 51, 63);
               width: auto;
               cursor: pointer;
               user-select: none;
               background-color: rgb(255, 255, 255);
               border: 1px solid rgba(49, 51, 63, 0.2);"
        onmouseover="this.style.backgroundColor='rgba(151, 166, 195, 0.15)'"
        onmouseout="this.style.backgroundColor='rgb(255, 255, 255)'"
        onmousedown="this.style.backgroundColor='rgba(151, 166, 195, 0.25)'"
        onmouseup="this.style.backgroundColor='rgba(151, 166, 195, 0.15)'">
        Copy
    </button>
    </div>
    """
    return components.html(copy_js, height=45)

# Streamlit UI
st.title("GenAI Translator")

# Create a layout for input text area and copy button
input_header_col, copy_button_col = st.columns([5, 1])

with input_header_col:
    st.write("Enter text to translate:")

# Input text area with a unique key
input_text = st.text_area("", height=400, key="input_text_area", label_visibility="collapsed")
st.caption(f"Character count: {len(input_text)} | Approximate token count: ~{len(input_text) // 4}")

# Copy button for input text (always display)
with copy_button_col:
    create_copy_button(input_text, "input")

# Language selection
col1, col2 = st.columns(2)
with col1:
    # Add more languages as needed
    source_lang = st.selectbox("Source Language", ["English", "Spanish", "German", "Vietnamese"])
with col2:
    # Add more languages as needed
    target_lang = st.selectbox("Target Language", ["English", "Spanish", "German", "Vietnamese"])

# Model selection
selected_model = st.selectbox("Select AI Model", AI_MODELS)

# Translation settings
with st.expander("Advanced Settings"):
    chunk_size = st.slider("Max chunk size (characters)", 500, 4000, 1500, 
                          help="Larger chunks may improve coherence but could be less reliable for very long texts")

# Translate button
if st.button("Translate"):
    if input_text and source_lang != target_lang:
        with st.spinner("Translating..."):
            if len(input_text) > chunk_size:
                st.info(f"Text is {len(input_text)} characters long. It will be processed in chunks")
            translated_text = translate_text(input_text, source_lang, target_lang, selected_model)
        
        # Create a layout for translated text and copy button
        output_header_col, output_copy_button_col = st.columns([5, 1])
        
        with output_header_col:
            st.subheader("Translated Text:")
        
        translated_text_area = st.text_area("", value=translated_text, height=400, key="output_text_area", label_visibility="collapsed")
        
        # Copy button for translated text
        with output_copy_button_col:
            create_copy_button(translated_text, "output")
            
        st.download_button(
            label="Download translation",
            data=translated_text,
            file_name=f"translation_{source_lang}_to_{target_lang}.txt",
            mime="text/plain"
        )
    elif source_lang == target_lang:
        st.warning("Please select different languages for source and target.")
    else:
        st.warning("Please enter some text to translate.")

# Add a note about the API usage
st.sidebar.markdown("This translator uses the OpenRouter API to access various AI models for translation.")
st.sidebar.markdown("Different models may have different capabilities and performance characteristics.")
