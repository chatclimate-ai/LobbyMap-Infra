import streamlit as st
import random
import requests
import datetime
import time


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

        # Additional fields from the new payload:
        stance = evidence_item.get("stance")  # e.g. -2 to +2
        stance_text = evidence_item.get("stance_text")  # string explanation
        confidence_score = evidence_item.get("confidence_score", 0.0)
        rank_score = evidence_item.get("rank_score", 0.0)

        # 1) Display truncated content with a popover for the full text
        if content:
            st.text(truncate_content(f"{content}\n\n", 30))
            with st.popover("Read more"):
                st.text(content)

        # 2) Display metadata
        with st.expander("View Metadata"):
            st.markdown(f"- **Date:** {doc.get('date', 'N/A')}")
            st.markdown(f"- **File Name:** {doc.get('file_name', 'N/A')}")
            st.markdown(f"- **Region:** {doc.get('region', 'N/A')}")
            st.markdown(f"- **Author:** {doc.get('author', 'N/A')}")

        # 3) Removal & Ranking Controls
        chunk_key = f"msg_{msg_index}_chunk_{idx}"
        if chunk_key not in st.session_state.removals:
            st.session_state.removals[chunk_key] = False
        removal_state = st.session_state.removals[chunk_key]
        icon_path = "../images/removed-bin.png" if removal_state else "../images/bin.png"

        if chunk_key not in st.session_state.ranks:
            st.session_state.ranks[chunk_key] = idx
        rank_options = [i + 1 for i in range(total_chunks)]  # Start from 1 in the dropdown
        stance_data = st.session_state.generated_stances.get(chunk_key, {"stance": None, "stance_text": ""})

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
                        # sleep to simulate a long-running process
                        time.sleep(3)
                        # Mockup response for stance generation
                        stance_payload = {
                            "stance": random.randint(-2, 2),
                            "stance_text": "Mockup stance text explaining the evidence stance.",
                        }
                        st.session_state.generated_stances[chunk_key] = {
                            **stance_payload,
                            "updated_generated_stance": stance_payload["stance"]  # Default to generated stance
                        }
                        st.rerun()

        if not removal_state:
            # Display the stance score as a dropdown
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


def render_sidebar():
    """
    Render the sidebar with filtering options and a "Clear Chat" button.
    Returns the user's input for filtering and how many docs to retrieve.
    """
    st.sidebar.header("Filter Options")
    author = st.sidebar.text_input('Author (optional)')
    date = st.sidebar.text_input('Date (optional)')
    region = st.sidebar.text_input('Region (optional)')
    filename = st.sidebar.text_input('Filename (optional)')
    num_documents = st.sidebar.number_input(
        'Number of documents to return',
        min_value=1,
        value=5
    )

    if st.sidebar.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.removals = {}
        st.session_state.ranks = {}
        st.rerun()

    return author, date, region, filename, num_documents


def handle_chat_input(author, date, region, filename, num_documents):
    """
    Handles user input via the chat_input widget. Fetches mock results,
    stores them, and triggers a rerun to display the updated conversation.
    """
    prompt = st.chat_input("Ask our search engine...")
    if not prompt:
        return

    # Add user message to session
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Retrieving information..."):
        params = {'query': prompt}
        if author:
            params['author'] = author
        if date:
            params['date'] = date
        if region:
            params['region'] = region
        if filename:
            params['file_name'] = filename
        params['top_k'] = num_documents

        # Mock call to RAG API
        response = {
            "pdf_docs": {
                "search": {
                    "query": "energy transition & zero carbon technologies",
                    "author": "CEZ",
                    "date": "",
                    "region": "",
                    "file_name": "",
                    "top_k": 4
                },
                "artifacts": {
                    "parser": {
                        "model_name": "docling",
                        "options": {
                            "do_ocr": True,
                            "ocr_options": "easyocr",
                            "do_table_structure": True,
                            "do_cell_matching": False,
                            "tableformer_mode": "ACCURATE",
                            "images_scale": 1.0,
                            "generate_page_images": False,
                            "generate_picture_images": False,
                            "backend": "docling",
                            "embed_images": False
                        }
                    },
                    "rag_components": {
                        "chunking_method": "layout",
                        "chunking_similarity_threshold": 8000,
                        "vectorizer_model_name": "bge-m3",
                        "reranker_model_name": "BAAI/bge-reranker-v2-m3"

                    }
                },
                "evidences": [
                    {
                        "evidence": {
                            "content": "## BRIEFING PAPER FEBRUARY 2017\n## CLIMATE & ENERGY SNAPSHOT: CZECH REPUBLIC\n## THE POLITICAL ECONOMY OF THE LOWCARBON TRANSITION\nJULIAN SCHWARTZKOPFF, SABRINA SCHULZ & ALEXANDRA GORITZ\nThis Briefing Paper presents an assessment of the political economy of the Czech Republic with regard to the loW-carbon transition. This paper is of a series of briefings on the four Central European states forming the \"Visegrad Group\" . Often  perceived as one unified bloc working against the low-carbon transition, E3G digs deeper and studies their specificities, their influence and their   particular social and economical interests, in order to identify opportunities to accelerate the low-carbon transition, domestically, and at the European level: part\nglobal  low-carbon transition is underway, but not all countries are actively participating: Engaging as early as possible, however; is crucial to reap benefits of lowcarbon development while avoiding economic losses through stranded assets and abrupt economic shifts. In the European Union (EU), the Visegrad Group in particular is   often seen to be attempting to slow down the low-carbon transition, both domestically and by opposing stronger EU climate action.\nAgainst this background, E3G has applied its Political Economy Mapping Methodology (PEMM) to the Visegrad states plus Romania and Bulgaria. The process involves extensive desk-based research as well as stakeholder interviews to identify the factors influencing country's position on energy and climate issues. The \"Climate & Energy   Snapshot\" series summarises the main findings into digestible   country briefings. All briefings will be published over the course of 2017. key\nWhen taking a closer   look, it becomes  apparent that there are considerable differences and disagreements between the countries. Identifying these discrepancies is crucial for designing country-specific intervention and cooperation opportunities that support a loW-carbon transition.",
                            "date": "2017",
                            "file_path": "data/Goku/pdf_files/-000-370-CEZ-Group_E3G_Czech-Energy-Snapshot_25-07-2018.pdf",
                            "page_count": 25,
                            "title": "",
                            "file_name": "-000-370-CEZ-Group_E3G_Czech-Energy-Snapshot_25-07-2018.pdf",
                            "region": "",
                            "author": "CEZ"
                        },
                        "confidence_score": 0.7771179676055908,
                        "rank_score": 0.3684056955947133,
                        "stance": -1,
                        "stance_text": "The evidence suggests that the Czech Republic, along with other Visegrad Group countries..."
                    },
                    {
                        "evidence": {
                            "content": "## Public goods\n## Summary assessment:\nConcern for social issues may offer opportunities to promote action towards a low-carbon transition when a link to environmental problems can be established.",
                            "date": "2017",
                            "file_path": "data/Goku/pdf_files/-000-370-CEZ-Group_E3G_Czech-Energy-Snapshot_25-07-2018.pdf",
                            "page_count": 25,
                            "title": "",
                            "file_name": "-000-370-CEZ-Group_E3G_Czech-Energy-Snapshot_25-07-2018.pdf",
                            "region": "",
                            "author": "CEZ"
                        },
                        "confidence_score": 0.7646533250808716,
                        "rank_score": 0.08945460216888064,
                        "stance": 0,
                        "stance_text": "The evidence focuses on social issues and their potential link to environmental problems..."
                    },
                    {
                        "evidence": {
                            "content": "## Technology and innovation capability\n## Summary assessment:\nAlthough technology and innovation capability is a significant strength of the Czech   economy, these efforts are not geared towards a low-carbon transition. vet",
                            "date": "2017",
                            "file_path": "data/Goku/pdf_files/-000-370-CEZ-Group_E3G_Czech-Energy-Snapshot_25-07-2018.pdf",
                            "page_count": 25,
                            "title": "",
                            "file_name": "-000-370-CEZ-Group_E3G_Czech-Energy-Snapshot_25-07-2018.pdf",
                            "region": "",
                            "author": "CEZ"
                        },
                        "confidence_score": 0.7746239900588989,
                        "rank_score": 0.0793528944558775,
                        "stance": -2,
                        "stance_text": "The evidence explicitly states that technology and innovation capability..."
                    },
                    {
                        "evidence": {
                            "content": "## About E3G\nE3G is an independent, non-profit European organisation operating in the public interest to accelerate the global transition to sustainable development: E3G builds cross-sectoral coalitions to achieve carefully defined outcomes, chosen for their capacity to leverage   change. E3G works closely with like-minded partners in government,  politics, business, civil   society, science, the media,  public   interest foundations and elsewhere:\nMore information is available at WWW.e3g org",
                            "date": "2017",
                            "file_path": "data/Goku/pdf_files/-000-370-CEZ-Group_E3G_Czech-Energy-Snapshot_25-07-2018.pdf",
                            "page_count": 25,
                            "title": "",
                            "region": "",
                            "file_name": "-000-370-CEZ-Group_E3G_Czech-Energy-Snapshot_25-07-2018.pdf",
                            "author": "CEZ"
                        },
                        "confidence_score": 0.7634724974632263,
                        "rank_score": 0.012147170099805137,
                        "stance": 0,
                        "stance_text": "This evidence provides information about E3G but does not directly address the energy transition..."
                    }
                ]
            }
        }

        # Store the assistant's response in session state
        st.session_state.messages.append({
            "role": "assistant",
            "pdf_docs": response["pdf_docs"]
        })
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

        generated_stance = evidence_item.get("stance", 0)
        generated_stance_reason = evidence_item.get("stance_text", "")
        confidence_score = evidence_item.get("confidence_score", 0.0)
        rank_score = evidence_item.get("rank_score", 0.0)

        # Use the same chunk_key format as in render_pdf_docs
        chunk_key = f"msg_{msg_index}_chunk_{idx}"
        removal_state = st.session_state.removals.get(chunk_key, False)
        user_selected_rank = st.session_state.ranks.get(chunk_key, idx)

        status = "rejected" if removal_state else "approved"
        updated_status = status
        generated_stance_score = round(random.uniform(0, 1), 2)
        updated_generated_stance = st.session_state.generated_stances.get(chunk_key, {}).get("updated_generated_stance")

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
            "rank": idx,
            "status": "approved",
            "confidence_score": confidence_score,
            "rank_score": rank_score,
            "generated_stance": generated_stance,
            "generated_stance_reason": generated_stance_reason,
            "generated_stance_score": generated_stance_score,
            "updated_rank": user_selected_rank,
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
    set_page_layout()
    create_header()
    initialize_states()

    with st.container():
        display_chat_history()

    author, date, region, filename, num_documents = render_sidebar()
    handle_chat_input(author, date, region, filename, num_documents)


if __name__ == "__main__":
    main()
