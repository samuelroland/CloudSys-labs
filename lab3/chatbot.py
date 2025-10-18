# Based on the app of Abir Chebbi (abir.chebbi@hesge.ch)
# Modified for the Switch Engine+Azure Cosmos DB+Google Vertex AI
# Helped by ChatGPT
from google.genai import Client
from google.oauth2 import service_account
from azure.cosmos import CosmosClient
import streamlit as st
import configparser
from langchain_core.prompts import PromptTemplate

# same model as vectorise-store.py
ai_model = "gemini-embedding-001"


def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config


config = load_config()

azure_account_name = config.get('azure', 'account_name')
azure_container_name = config.get('azure', 'container_name')
vertexai_project_id = config.get('vertexai', 'project_id')

region = 'us-central1'

# configuring streamlit page settings
st.set_page_config(
    page_title="cloud lecture lab",
    page_icon="💬",
    layout="centered"
)

# streamlit page title
st.title("Chat with your lecture")


# CosmoDB client
def get_cosmos_client():
    cosmos_url = "https://{0}.documents.azure.com:443/".format(
        azure_account_name)
    # TODO: pass that as arguments ?
    with open('azure-db-key.txt', 'r') as file:
        key = file.read().rstrip()
    return CosmosClient(cosmos_url, credential=key)


def get_embedding(text):
    # the key is only useful when the gcloud auth login is not done
    scopes = ['https://www.googleapis.com/auth/cloud-platform']
    creds = service_account.Credentials.from_service_account_file(
        "vertexai-service-account-key.json", scopes=scopes)
    client = Client(vertexai=True, project=vertexai_project_id,
                    location=region)

    result = client.models.embed_content(
        model=ai_model,
        contents=text,
    )
    return result.embeddings


# Cosmos DB equivalent of similarity_search()
def similarity_search_cosmos_db(embed_query, vector_field='vector_field', top_k=5):
    vector_query = {
        "vector": embed_query,
        "topK": top_k,
        "vectorField": vector_field,
        "similarityFunction": "cosine"  # or 'euclidean', 'dotProduct'
    }

    query = {
        "filter": "",
        "vectorSearch": vector_query
    }

    client = get_cosmos_client()
    database = client.get_database_client(azure_account_name)
    container = database.get_container_client(azure_container_name)

    return list(container.query_items(
        query=query,
        enable_vector_search=True
    ))


def prepare_prompt(question, context):
    template = """
    You are a Professor. The student will ask you a questions about the lecture. 
    Use following piece of context to answer the question. 
    If you don't know the answer, just say you don't know. 

    Context:   <context>
    {context}
    </context>
    Question: {question}
    Answer: 

    """

    prompt = PromptTemplate(
        template=template,
        input_variables=['context', 'question']
    )
    prompt_formatted_str = prompt.format(context=context, question=question)
    return prompt_formatted_str


def generate_answer(prompt):
    # Try multiple Gemini model names in order of preference
    model_names = [
        "gemini-2.5-flash-lite",
    ]

    for model_name in model_names:
        try:
            client = Client(
                vertexai=True, project=vertexai_project_id, location=region)
            print(f"Using chat model: {model_name}")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            return response.prompt_feedback
        except Exception as e:
            print(f"Model {model_name} not available: {e}")
            continue

    raise ValueError(
        "No Gemini model available. Please check your Vertex AI model access.")


# The entrypoint of the core logic, to be called by test.py
def generate_ai_answer(user_prompt):
    embed_question = get_embedding(user_prompt)
    print(embed_question)
    sim_results = similarity_search_cosmos_db(embed_question)
    context = [i['_source']['text'] for i in sim_results]
    print(context)
    prompt = prepare_prompt(user_prompt, context)
    print(prompt)
    return generate_answer(prompt)


def main():

    # initialize chat session in streamlit if not already present
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # input field for user's message
    user_prompt = st.chat_input("Ask a question for your knowledge base")

    if user_prompt:
        # add user's message to chat and display it
        st.chat_message("user").markdown(user_prompt)
        st.session_state.chat_history.append(
            {"role": "user", "content": user_prompt})
        # Generate and display answer
        print(user_prompt)

        answer = generate_ai_answer(user_prompt)
        st.session_state.chat_history.append(
            {"role": "system", "content": answer.content})
        for message in st.session_state.chat_history[-1:]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])


if __name__ == "__main__":
    main()
