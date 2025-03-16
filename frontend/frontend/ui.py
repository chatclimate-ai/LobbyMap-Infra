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
    col1, col2 = st.columns([0.5, 8])
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
    Render documents stored under the 'pdf_docs' structure:
      {
        "search": {...},
        "evidences": [ ... ]
      }
    """
    query = pdf_docs_struct.get("search", {}).get("query", "")
    pdf_evidences = pdf_docs_struct.get("evidences", [])
    total_chunks = len(pdf_evidences)

    if not pdf_evidences:
        st.markdown("No results found.")
        return

    # ---------------------
    # Iterate over each evidence
    for idx, evidence_item in enumerate(pdf_evidences):
        doc = evidence_item.get("evidence", {})
        content = doc.get("content", "").strip()
        author = doc.get("author", "N/A")
        date = doc.get("date", "N/A")
        region = doc.get("region", "N/A")
        file_name = doc.get("file_name", "N/A")
        conf_score = evidence_item.get("confidence_score", 0.0)
    
        # 1) Display truncated content with a popover for the full text
        if content:
            # st.text(truncate_content(f"{content}\n\n", 30))
            # with st.popover("Read more"):
            #     st.text(content)
            st.text(truncate_content(f"{content}\n\n", 30))
            col1, col2 = st.columns([1, 1])

            with col1:
                with st.popover("Read more"):
                    st.text(content)
            
            with col2:
                with st.popover("Reveal score"):
                    st.markdown(f"Confidence Score: {conf_score:.3f}")

        # 2) Display metadata
        with st.expander("View Metadata"):
            st.markdown(f"- **Date:** {date}")
            st.markdown(f"- **File Name:** {file_name}")
            st.markdown(f"- **Region:** {region}")
            st.markdown(f"- **Author:** {author}")

        # 3) Removal & Ranking Controls
        chunk_key = f"msg_{msg_index}_chunk_{idx}"
        if chunk_key not in st.session_state.removals:
            st.session_state.removals[chunk_key] = False

        removal_state = st.session_state.removals[chunk_key]
        icon_path = "../images/removed-bin.png" if removal_state else "../images/bin.png"

        if chunk_key not in st.session_state.ranks:
            st.session_state.ranks[chunk_key] = idx
        rank_options = [i + 1 for i in range(total_chunks)]  # Start from 1 in the dropdown

        if chunk_key not in st.session_state.generated_stances:
            st.session_state.generated_stances[chunk_key] = {
                "stance": None, 
                "stance_text": None, 
                "stance_score": None, 
                "updated_generated_stance": None
                }

        col_icon, col_button, col_rank, col_stance = st.columns([0.2, 1.5, 1.5, 1.5])
        with col_icon:
            st.image(icon_path, width=30)

        with col_button:
            label_text = "Unremove" if removal_state else "Remove"
            if st.button(label_text, key=f"toggle_{chunk_key}"):
                st.session_state.removals[chunk_key] = not removal_state
                st.rerun()

        with col_rank:
            if not removal_state:
                selected_rank_ui = st.selectbox(
                    "Rank:",
                    rank_options,
                    index=st.session_state.ranks[chunk_key],
                    key=f"{chunk_key}_rank_select"
                )
                st.session_state.ranks[chunk_key] = selected_rank_ui - 1

        with col_stance:
            if not removal_state:
                if st.button("Generate Stance", key=f"generate_stance_{chunk_key}"):
                    with st.spinner("Generating stance..."):
                        # Make stance generation call
                        stance_payload = generator_call(
                            query=query,
                            evidence=content,
                            # author=author
                        )
                        st.session_state.generated_stances[chunk_key] = {
                            **stance_payload,
                            "updated_generated_stance": stance_payload["stance"]  # Default to generated stance
                        }
                        st.rerun()
        
        if not removal_state:
            # Display the stance score as a dropdown
            stance_data = st.session_state.generated_stances[chunk_key]
            if stance_data["stance"] is not None:
                # Dropdown options for stance values
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
                st.session_state.generated_stances[chunk_key]["updated_generated_stance"] = selected_stance


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
                st.markdown(f"**Stance Explanation:** {stance_data['stance_text']}")

        st.markdown(f"{'-' * 50}\n\n")

    # ----------------------
    # SINGLE "Send Feedback" BUTTON for the entire set of evidences
    # (Ensures a unique key by including msg_index)
    if st.button("Send Feedback", key=f"send_feedback_{msg_index}"):
        feedback_payloads = build_feedback_payloads(
            {"pdf_docs": pdf_docs_struct},
            msg_index=msg_index
        )

        all_success = True  # To track if all requests succeed
        for idx, payload in enumerate(feedback_payloads):
            try:
                response_api = requests.post("http://feedback_api:8000/feedback/", json=payload)
                response_api.raise_for_status()  # Raise an error for HTTP issues
            except requests.exceptions.RequestException as e:
                all_success = False  # If any request fails, set to False

                # Try to extract the response details for better error reporting
                if hasattr(e, 'response') and e.response is not None:
                    error_message = e.response.text  # Extract error response body
                    error_status = e.response.status_code  # Extract HTTP status code
                    st.error(f"Error for payload {idx + 1}: {error_status} - {error_message}")
                else:
                    st.error(f"Failed to send feedback for payload {idx + 1}: {str(e)}")

                # Optionally break the loop to stop further processing
                break

        if all_success:
            # Show a toast-like notification
            st.success("Feedback successfully sent!")


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
    col1, col2, col3 = st.columns([4, 1, 1], gap="small", vertical_alignment="bottom")
    if "query_select" not in st.session_state:
        st.session_state["query_select"] = "Select a query..."

    with col1:
        queries = ["Select a query..."] + [p["query"] for p in list_prompts(PROMPT_MAP)]
        st.selectbox(
            "Select a query...", 
            queries, 
            label_visibility="collapsed", 
            key="query_select"
            )


    with col2:
        if st.button("📤", help="upload files", key="upload_icon"):
            st.session_state.show_upload_dialog = True

    with col3:
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
    
    selected_query = st.session_state["query_select"]
    if selected_query == "Select a query...":
        return
    
    # Do your retrieval logic here:
    prompt = next((p["prompt"] for p in list_prompts(PROMPT_MAP) 
                   if p["query"] == selected_query), "")
    
    # Add user message to session
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Retrieving information..."):
        # Make retriever call
        response = retriever_call(
            query=prompt,
            author=author,
            date=date,
            region=region,
            file_name=filename,
            top_k=num_documents
        )

    # Store the assistant's response in session state
    st.session_state.messages.append({
        "role": "assistant",
        "pdf_docs": response["pdf_docs"]
    })
    del st.session_state["query_select"]
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
