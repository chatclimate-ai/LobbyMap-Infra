import streamlit as st
import requests
import datetime
import yaml
import os
from utils import retriever_call, generator_call, upload_call, list_collection, get_collections, save_collection, add_to_collection, check_file_in_map, list_prompts, delete_prompt, delete_call


config_path = "/app/config.yaml"
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

FILE_SYSTEM = config["Backend"]["file_system"]
FILE_SYSTEM_SERVER = config["Backend"]["file_system_server"]
DATA_MAP = FILE_SYSTEM + "/" + config["Backend"]["data_map"]
PROMPT_MAP = FILE_SYSTEM + "/" + config["Backend"]["prompt_map"]

def set_page_layout():
    """
    Configure the Streamlit page layout and inject custom CSS.
    """
    st.set_page_config(layout="centered")
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 900px; /* Adjust this value to set the desired width */
            margin: auto;
            padding: 2rem;
        }
        .st-chat {
            max-width: 100%;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def create_header():
    """
    Display the app's header with a logo and a title.
    """
    col1, col2 = st.columns([0.5, 8], gap="small", vertical_alignment="bottom")
    col1.image("../images/logo.jpg", width=78)
    col2.title("LobbyMap Search")


def initialize_states():
    """
    Initialize all necessary variables in st.session_state.
    """
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "removals" not in st.session_state:
        st.session_state.removals = {}

    if "ranks" not in st.session_state:
        st.session_state.ranks = {}

    if "generated_stances" not in st.session_state:
        st.session_state.generated_stances = {}
    
    if "selected_sidebar" not in st.session_state:
        st.session_state.selected_sidebar = "Filters"

    if "selected_file" not in st.session_state:
        st.session_state.selected_file = None
    
    if "show_upload_dialog" not in st.session_state:
        st.session_state.show_upload_dialog = False
    
    if "selected_prompt" not in st.session_state:
        st.session_state.selected_prompt = None


def truncate_content(text, word_limit):
    """
    Truncate text to a specified number of words.
    """
    words = text.split()
    if len(words) > word_limit:
        return ' '.join(words[:word_limit]) + '...'
    return text


def display_chat_history():
    """
    Display the messages in the chat.
    """
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and "pdf_docs" in message:
                # 'pdf_docs' is a dict with {'search': {...}, 'evidences': [...]}
                pdf_docs_struct = message["pdf_docs"]
                render_pdf_docs(i, pdf_docs_struct)
            else:
                st.markdown(message["content"])



def render_pdf_docs(msg_index: int, pdf_docs_struct: dict):
    """
    Render a user-friendly interface to review and interact with evidence from PDF documents.
    """
    query = pdf_docs_struct.get("search", {}).get("query", "")
    pdf_evidences = pdf_docs_struct.get("evidences", [])
    total_chunks = len(pdf_evidences)

    if not pdf_evidences:
        st.warning("⚠️ No relevant evidence found.")
        return

    # ---------- Summary Table ----------
    st.markdown("### 📊 Summary of Retrieved Evidence")
    summary_rows = [
        {
            "Chunk": i + 1,
            "File": e["evidence"].get("file_name", "N/A"),
            "Date": e["evidence"].get("date", "N/A"),
            "Region": e["evidence"].get("region", "N/A"),
            "Confidence": round(e.get("confidence_score", 0.0), 3),
            "Evidence": e["evidence"].get("content", ""),
        }
        for i, e in enumerate(pdf_evidences)
    ]
    st.dataframe(summary_rows, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ---------- Evidence Review ----------
    for idx, evidence_item in enumerate(pdf_evidences):
        doc = evidence_item.get("evidence", {})
        content = doc.get("content", "").strip()
        author = doc.get("author", "N/A")
        date = doc.get("date", "N/A")
        region = doc.get("region", "N/A")
        file_name = doc.get("file_name", "N/A")
        conf_score = evidence_item.get("confidence_score", 0.0)

        chunk_key = f"msg_{msg_index}_chunk_{idx}"
        st.session_state.removals.setdefault(chunk_key, False)
        st.session_state.ranks.setdefault(chunk_key, idx)
        st.session_state.generated_stances.setdefault(chunk_key, {
            "stance": None,
            "stance_text": None,
            "stance_score": None,
            "updated_generated_stance": None
        })

        st.markdown(f"### 🧩 Evidence {idx + 1} of {total_chunks}")
        st.text(f"> {truncate_content(content, 30)}")

        with st.expander("🔎 Full Content & Metadata"):
            st.text(content)
            st.markdown("---")
            st.markdown(f"**📄 File:** `{file_name}`")
            st.markdown(f"**📅 Date:** `{date}`")
            st.markdown(f"**🌍 Region:** `{region}`")
            st.markdown(f"**✍️ Author:** `{author}`")
            st.markdown(f"**📈 Confidence Score:** `{conf_score:.3f}`")
           

        # ---- Controls: Remove / Rank / Generate ----
        col1, col2, col3 = st.columns([1, 1, 1], vertical_alignment="bottom")

        with col1:
            remove_label = "✅ Keep" if st.session_state.removals[chunk_key] else "🗑️ Remove"
            if st.button(remove_label, key=f"remove_{chunk_key}", use_container_width=True):
                st.session_state.removals[chunk_key] = not st.session_state.removals[chunk_key]
                st.rerun()

        with col2:
            if not st.session_state.removals[chunk_key]:
                rank = st.selectbox(
                    "rank",
                    options=[f"🔢 Rank {i + 1}" for i in range(total_chunks)],
                    index=st.session_state.ranks[chunk_key],
                    key=f"rank_{chunk_key}",
                    label_visibility="collapsed",
                )
                st.session_state.ranks[chunk_key] = int(rank.split(" ")[-1]) - 1

        with col3:
            if not st.session_state.removals[chunk_key]:
                if st.button("🧠 Generate Stance", key=f"genstance_{chunk_key}", use_container_width=True):
                    with st.spinner("Analyzing stance..."):
                        stance_payload = generator_call(query=query, evidence=content)
                        st.session_state.generated_stances[chunk_key].update({
                            **stance_payload,
                            "updated_generated_stance": stance_payload["stance"]
                        })
                        st.rerun()

        # ---- Stance Review and Selection ----
        if not st.session_state.removals[chunk_key]:
            stance_data = st.session_state.generated_stances[chunk_key]
            if stance_data["stance"] is not None:
                stance_options = [-2, -1, 0, 1, 2]

                # Default selected value
                default_stance = stance_data.get("updated_generated_stance", stance_data["stance"])

                # Create a dropdown for the stance score
                selected_stance = st.selectbox(
                    "Stance Score",
                    options=stance_options,
                    index=stance_options.index(default_stance),
                    key=f"stance_dropdown_{chunk_key}"
                )
                # Store the updated stance in session state
                if selected_stance != st.session_state.generated_stances[chunk_key]["updated_generated_stance"]:
                    st.session_state.generated_stances[chunk_key]["updated_generated_stance"] = selected_stance
                    st.rerun()


                # Determine box and background colors based on selected stance value
                if selected_stance > 0:
                    border_color = "green"
                    background_color = "#e6ffe6"  # Light green background
                elif selected_stance < 0:
                    border_color = "red"
                    background_color = "#ffe6e6"  # Light red background
                else:
                    border_color = "blue"
                    background_color = "#e6f0ff"  # Light blue background

                # Display the colored box based on the selected stance value
                st.markdown(
                    f"""
                            <div style='
                                border: 2px solid {border_color};
                                border-radius: 10px;
                                padding: 6px;
                                display: inline-block;
                                color: black;
                                font-weight: bold;
                                background-color: {background_color};
                                margin-bottom: 10px;
                            '>
                                Stance: {selected_stance}
                            </div>
                            """,
                    unsafe_allow_html=True
                )

            # Display stance explanation below the row
            if stance_data["stance_text"]:
                st.markdown(f"📖 **Stance Explanation:** {stance_data['stance_text']}")

        st.markdown("---")

    # ---------- Final Feedback Button ----------
    st.markdown("### ✅ Final Step")
    if st.button("📤 Send Feedback", key=f"send_feedback_{msg_index}"):
        feedback_payloads = build_feedback_payloads(
            {"pdf_docs": pdf_docs_struct},
            msg_index=msg_index
        )

        all_success = True
        for idx, payload in enumerate(feedback_payloads):
            try:
                response_api = requests.post("http://feedback_api:8000/feedback/", json=payload)
                response_api.raise_for_status()
            except requests.exceptions.RequestException as e:
                all_success = False
                if hasattr(e, 'response') and e.response:
                    st.error(f"Chunk {idx + 1} failed: {e.response.status_code} - {e.response.text}")
                else:
                    st.error(f"Chunk {idx + 1} failed: {str(e)}")
                break

        if all_success:
            st.success("🎉 All feedback successfully submitted!")



def show_prompt_info(
        selected_prompt: dict,
    ):
    """
    Display prompt information in a container.
    """
    with st.container():
        st.markdown(
            f"""
            # {selected_prompt["query"]}

            --------------------------------
            #### Pompt: 
            {selected_prompt["prompt"]}
            """, unsafe_allow_html=True)

def show_file_info(
        file_name: str,
        author: str = "Unknown",
        date: str = "Unknown",
        region: str = "Unknown",
        size: float = 0.0,
        url: str = "",
        num_chunks: int = 0,
        # uploaded_time: str = "",
        language: str = "Unknown"
    ):
    """
    Display file information in a container.
    """
    if not author:
        author = "Unknown"
    if not date:
        date = "Unknown"
    if not region:
        region = "Unknown"
    if not size:
        size = 0.0
    if " " in url:
        url = f"<{url}>"
    # if not uploaded_time:
    #     uploaded_time = "Unknown"
    if not language:
        language = "Unknown"

    with st.container():
        st.markdown(
            f"""
            ## {file_name}

            Size: {size} MB

            Chunks: {num_chunks}

            [View File]({url})

            #### Metadata

            **Author:** {author}

            **Date:** {date}

            **Region:** {region}

            **Language:** {language}

            """, unsafe_allow_html=True)


def filter_options():
    """
    Default filter options for the sidebar.
    """
    st.header("Filter Options")
    author = st.text_input('Author (optional)').lower()
    date = st.text_input('Date (optional)').lower()
    region = st.text_input('Region (optional)').lower()
    filename = st.text_input('Filename (optional)')

    num_documents = st.number_input(
        'Maximum number of extracts',
        min_value=1,
        value=5
    )

    min_confidence = st.slider(
        "Minimum Confidence Score",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.01
    )

    toggle = st.toggle("Use the confidence score", False)

    if toggle:
        return author, date, region, filename, min_confidence

    return author, date, region, filename, num_documents


@st.dialog("Add a Prompt")
def new_prompt_dialog():
    query = st.text_input("Query")
    prompt = st.text_input("Prompt")

    col1, col2 = st.columns([1, 1], gap="small", vertical_alignment="top")

    with col1:
        if st.button("Save"):
            if not query.strip():
                st.warning("Please enter a query.")
            elif not prompt.strip():
                st.warning("Please enter a prompt.")
            else:
                new_prompt = {
                    "query": query,
                    "prompt": prompt
                }

                add_to_collection(PROMPT_MAP, new_prompt)
                st.rerun()

    with col2:
        if st.button("Cancel", key="cancel_upload"):
            st.rerun()




def render_sidebar():
    """
    Render the sidebar with filtering options.
    Returns the user's input for filtering and how many docs to retrieve.
    """
    author, date, region, filename, num_documents = None, None, None, None, 5

    with st.sidebar:
        col1, col2 = st.columns([1, 4], gap="small", vertical_alignment="top")

        with col1:
            if st.button("⚙️", key="icon_button_1", help="Filters"):
                st.session_state.selected_sidebar = "Filters"

            if st.button("🗄️", key="icon_button_2", help="Files"):
                if st.session_state.selected_file:
                    st.session_state.selected_file = None
                    st.session_state.selected_sidebar = "Files"
                    st.rerun()
                
                else:
                    # If already in files view, we don't reset anything
                    st.session_state.selected_sidebar = "Files"
            
            if st.button("📝", key="icon_button_3", help="Prompts"):
                if st.session_state.selected_prompt:
                    st.session_state.selected_prompt = None
                    st.session_state.selected_sidebar = "Prompts"
                    st.rerun()
                
                else:
                    # If already in files view, we don't reset anything
                    st.session_state.selected_sidebar = "Prompts"

        with col2:
            if st.session_state.selected_sidebar == 'Filters':
                author, date, region, filename, num_documents = filter_options()
            
            elif st.session_state.selected_sidebar == 'Prompts':
                st.header("Prompts")
                if st.session_state.selected_prompt:
                    # Display selected file details
                    selected_prompt = st.session_state.selected_prompt
                    show_prompt_info(selected_prompt)

                    if st.button("Delete", key="delete_prompt"):
                        delete_prompt(PROMPT_MAP, selected_prompt)
                        st.success("Prompt deleted successfully.")
                        st.session_state.selected_prompt = None
                        st.rerun()

                    # Back button to return to search view
                    if st.button("Back", key="back_button"):
                        st.session_state.selected_prompt = None
                        st.rerun()
                
                else:
                    if st.button("Add a prompt", key=f"add_prompt"):
                        new_prompt_dialog()

                    search_query = st.text_input("Search prompts", key="prompt_search")
                    all_prompt = list_prompts(PROMPT_MAP)


                    if search_query.strip():
                        filtered_prompt = [f for f in all_prompt if search_query.lower() in f["query"].lower()]

                    else:
                        filtered_prompt = all_prompt
                    
                    if not filtered_prompt:
                        st.write("No prompts match your search.")
                    
                    else:
                        for prompt in filtered_prompt:
                            with st.container():
                                if st.button(prompt["query"], key=f"prompt_{prompt["query"].split()[0]}"):
                                    st.session_state.selected_prompt = prompt
                                    st.rerun()
                    
            
            else:
                st.header("Files")
                # Check if a file has been selected
                if st.session_state.selected_file:
                    # Display selected file details
                    selected_file = st.session_state.selected_file
                    show_file_info(
                        file_name = selected_file["file_name"],
                        author = selected_file["author"],
                        date = selected_file["date"],
                        region = selected_file["region"],
                        size = selected_file["size"],
                        url = selected_file["url"],
                        num_chunks = selected_file["num_chunks"],
                        # uploaded_time = selected_file["upload_time"],
                        language = selected_file["language"]
                    )
               
                    
                    if st.button("Delete", key="delete_file"):
                        try:
                            delete_call(selected_file["file_name"])
                            st.success(f"File '{selected_file['file_name']}' deleted successfully.")
                            st.session_state.selected_file = None
                            st.rerun()
                        
                        except Exception as e:
                            st.error(f"An error occurred while deleting the file. {str(e)}")
                            st.rerun()
                
                
                    # Back button to return to search view
                    if st.button("Back", key="back_button"):
                        st.session_state.selected_file = None  # Reset selection
                        st.rerun()

                
                else:
                    # File search and list
                    search_query = st.text_input("Search files", key="file_search")

                    # Base list of files
                    all_files = list_collection(DATA_MAP)
            
                    # Reactive filtering
                    if search_query.strip():
                        filtered_files = [f for f in all_files if search_query.lower() in f["file_name"].lower()]
                    else:
                        filtered_files = all_files

                    if not filtered_files:
                        st.write("No files match your search.")
                    else:
                        for file in filtered_files:
                            with st.container():
                                if st.button(file["file_name"], key=f"file_{file["file_name"]}"):
                                    st.session_state.selected_file = file
                                    st.rerun()


    return author, date, region, filename, num_documents



@st.dialog("Upload File and Add Metadata")
def upload_dialog():
    uploaded_file = st.file_uploader("Choose a file", type=["pdf"])
    author = st.text_input("Author").lower()
    Date = st.text_input("Date").lower()
    Region = st.text_input("Region").lower()

    options = ["latin-based", "arabic-based", "bengali-based", "cyrillic-based", "devanagari-based", "chinese-traditional", "chinese-simplified", "japanese", "korean", "telugu", "kannada", "thai"]
    default_option = "latin-based"
    language = st.selectbox("Choose a language type:", options, index=options.index(default_option))

    # upload_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    col1, col2 = st.columns([1, 1], gap="small", vertical_alignment="top")

    with col1:
        if st.button("Save"):
            if not uploaded_file:
                st.warning("Please upload a file.")
            elif not author.strip():
                st.warning("Author field cannot be empty.")
            else:
                file_name = uploaded_file.name

                # Check if file already exists
                if check_file_in_map(file_name, DATA_MAP):
                    st.error(f"File '{file_name}' already exists.")
                    return

                size = uploaded_file.size / (1024 * 1024)
                os.makedirs(FILE_SYSTEM, exist_ok=True)
                url = f"{FILE_SYSTEM_SERVER}/{file_name}"
                file_path = f"{FILE_SYSTEM}/{file_name}"

                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                with st.spinner("Processing file..."):
                    # Make upload call
                    try:
                        num_chunks = upload_call(
                            file_path=file_path,
                            author=author,
                            date=Date,
                            region=Region,
                            size=size,
                            language=language,
                            # upload_time=upload_time
                        )["num_chunks"]

                        # Re-write the Data Map
                        new_file = {
                                "file_name": file_name,
                                "author": author,
                                "date": Date,
                                "degion": Region,
                                "size": size,
                                "url": url,
                                "language": language,
                                "num_chunks": num_chunks,
                                # "upload_time": upload_time
                            }
                        
                        add_to_collection(DATA_MAP, new_file)
                        st.session_state.upload_success = f"File '{file_name}' and metadata submitted."
                        st.rerun()
                    
                    except Exception as e:
                        # check if the file is actually in weaviate
                        existing_files = get_collections()["files"]
                        existing_file_names = [f["file_name"] for f in existing_files]
                        if file_name in existing_file_names:
                            st.session_state.upload_success = f"File '{file_name}' and metadata submitted."
                            st.rerun()


                        else:
                            st.session_state.upload_fail = f"An error occurred while processing the file {file_name}. Please try again. {str(e)}"
                            # delete the file 
                            # os.remove(file_path)
                            st.rerun()

    with col2:
        if st.button("Cancel", key="cancel_upload"):
            st.rerun()

    st.session_state.show_upload_dialog = False

def handle_chat_input(author, date, region, filename, num_documents):
    """
    Handles user input via the chat_input widget. Fetches mock results,
    stores them, and triggers a rerun to display the updated conversation.
    """
    col1, col2, col3, col4 = st.columns([4, 1, 1, 1], gap="small", vertical_alignment="bottom")


    if "process" not in st.session_state:
        st.session_state["process"] = False
    if "prompt_queue" not in st.session_state:
        st.session_state.prompt_queue = []
    if "failed_prompts" not in st.session_state:
        st.session_state.failed_prompts = []

    with col1:
        queries = ["All queries"] + [p["query"] for p in list_prompts(PROMPT_MAP)]
        options = st.multiselect(
            "Select a query ...",
            queries
        )

    with col2:
        if st.button("Process", key="process_button"):
            if options:
                st.session_state["process"] = True
            else:
                st.warning("No options selected.")

    with col3:
        if st.button("📤", help="upload files", key="upload_icon"):
            st.session_state.show_upload_dialog = True

    with col4:
        if st.button(
            label = "Clear Chat",
            key = "clear_chat",
            help = "Clear the chat history"
            ):
            st.session_state.messages = []
            st.session_state.removals = {}
            st.session_state.ranks = {}
            st.session_state.generated_stances = {}
            st.rerun()
    
    if st.session_state.show_upload_dialog:
        upload_dialog()

    if "upload_success" in st.session_state:
        st.success(st.session_state.upload_success)
        del st.session_state.upload_success
    
    if "upload_fail" in st.session_state:
        st.error(st.session_state.upload_fail)
        del st.session_state.upload_fail



    # --- Load Prompts on Process ---
    if st.session_state["process"]:
        if "All queries" in options:
            st.session_state.prompt_queue = list_prompts(PROMPT_MAP)
        else:
            st.session_state.prompt_queue = [
                prompt for prompt in list_prompts(PROMPT_MAP) if prompt["query"] in options
            ]
        st.session_state["process"] = False
        st.rerun()

    # --- Process Prompts One by One ---
    if st.session_state.prompt_queue:
        current_prompt = st.session_state.prompt_queue.pop(0)

        st.chat_message("user").markdown(current_prompt["query"])
        st.session_state.messages.append({
            "role": "user",
            "content": current_prompt["prompt"]
        })
        success = False
        with st.spinner(f"Retrieving information..."):
            for attempt in range(2):  # Try up to 2 times
                try:
                    response = retriever_call(
                        query=current_prompt["prompt"],
                        author=author,
                        date=date,
                        region=region,
                        file_name=filename,
                        top_k=num_documents
                    )

                    st.session_state.messages.append({
                        "role": "assistant",
                        "pdf_docs": response["pdf_docs"]
                    })
                    success = True
                    break  # Success, no need to retry

                except Exception as e:
                    error_message = str(e)

        if not success:
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"❌ **Failed to retrieve results** for: `{current_prompt['query']}`."
            })
            st.session_state.failed_prompts.append(current_prompt)

        st.rerun()
    # --- Retry UI for Failed Prompts ---
    if st.session_state.failed_prompts:
        st.markdown("---")
        st.markdown("### 🔁 Retry Failed Queries")
        for idx, failed_prompt in enumerate(st.session_state.failed_prompts):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{failed_prompt['query']}**")
            with col2:
                if st.button("Retry", key=f"retry_{idx}"):
                    st.session_state.prompt_queue.insert(0, failed_prompt)
                    st.session_state.failed_prompts.pop(idx)
                    st.rerun()



    
    


def build_feedback_payloads(response: dict, msg_index: int) -> list:
    """
    Build a list of feedback payloads for each evidence in the new RAG response.
    The output matches the EvidenceModel schema structure.
    """

    pdf_docs = response.get("pdf_docs", {})
    search_info = pdf_docs.get("search", {})
    evidences = pdf_docs.get("evidences", [])
    artifact_info = pdf_docs.get("artifacts", {})
    feedback_payloads = []

    for idx, evidence_item in enumerate(evidences):
        doc = evidence_item.get("evidence", {})
        file_name = doc.get("file_name", "")
        content = doc.get("content", "")
        author = doc.get("author")
        date = doc.get("date")
        region = doc.get("region")

        confidence_score = evidence_item.get("confidence_score", 0.0)
        rank_score = evidence_item.get("rank_score", 0.0)

        # Use the same chunk_key format as in render_pdf_docs
        chunk_key = f"msg_{msg_index}_chunk_{idx}"

        # Retrieve the stance data from session state
        stance_data = st.session_state.generated_stances[chunk_key]
        generated_stance = stance_data.get("stance")
        generated_stance_reason = stance_data.get("stance_text")
        generated_stance_score = stance_data.get("stance_score")
        updated_generated_stance = stance_data.get("updated_generated_stance")

        # Retrieve the removal state from session state
        removal_state = st.session_state.removals.get(chunk_key, False)
        updated_status = "rejected" if removal_state else "approved"
        
        # Retrieve the rank data from session state
        user_selected_rank = st.session_state.ranks.get(chunk_key, idx+1)


        feedback_item = {
            "search_elements": {
                "searched_query": search_info.get("query", ""),
                "searched_author": search_info.get("author", None),
                "searched_date": search_info.get("date", None),
                "searched_region": search_info.get("region", None),
                "searched_file_name": search_info.get("file_name", None),
                "top_k": search_info.get("top_k", 5)
            },
            "artifacts": artifact_info,
            "pdf_doc_name": file_name,
            "content": content,
            "author": author,
            "date": date,
            "region": region,
            "rank": idx+1,
            "status": "approved",
            "confidence_score": confidence_score,
            "rank_score": rank_score,
            "generated_stance": generated_stance,
            "generated_stance_reason": generated_stance_reason,
            "generated_stance_score": generated_stance_score,
            "updated_rank": user_selected_rank+1,
            "updated_status": updated_status,
            "updated_generated_stance": updated_generated_stance,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        feedback_payloads.append(feedback_item)

    return feedback_payloads


def main():
    """
    Main function to orchestrate the app:
    1. Set up the page layout
    2. Render the header and initialize session states
    3. Display existing chat messages
    4. Render the sidebar for filtering
    5. Handle new user input
    """
    existing_files = get_collections()["files"]
    save_collection(DATA_MAP, existing_files)

    set_page_layout()
    create_header()
    initialize_states()

    with st.container():
        display_chat_history()
    

    author, date, region, filename, num_documents = render_sidebar()
    handle_chat_input(author, date, region, filename, num_documents)

    



if __name__ == "__main__":
    main()
