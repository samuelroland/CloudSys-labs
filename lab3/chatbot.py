# Based on the app of Abir Chebbi (abir.chebbi@hesge.ch)
# Modified for the Switch Engine+Azure Cosmos DB+Google Vertex AI
# Helped by ChatGPT
from google.genai import Client
from google.oauth2 import service_account
from azure.cosmos import CosmosClient
import streamlit as st
import configparser
from langchain_core.prompts import PromptTemplate

def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config


config = load_config()

azure_account_name = config.get('azure', 'account_name')
azure_container_name = config.get('azure', 'container_name')
vertexai_project_id = config.get('vertexai', 'project_id')

# same model as vectorise-store.py
ai_model_embeddings = config.get('vertexai', 'ai_model_embeddings')
ai_model_final_prompt = config.get('vertexai', 'ai_model_final_prompt')

vertexai_region = config.get('vertexai', 'region')

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
    with open('azure-db-key.txt', 'r') as file:
        key = file.read().rstrip()
    return CosmosClient(cosmos_url, credential=key)


def get_vertex_ai_client():
    scopes = ['https://www.googleapis.com/auth/cloud-platform']
    creds = service_account.Credentials.from_service_account_file(
        "vertexai-service-account-key.json", scopes=scopes)
    return Client(vertexai=True, project=vertexai_project_id, location=vertexai_region, credentials=creds)


def get_embedding(text):
    client = get_vertex_ai_client()

    result = client.models.embed_content(
        model=ai_model_embeddings,
        contents=text,
    )
    return result.embeddings[0]  # the list contain a single element


# Cosmos DB equivalent of similarity_search()
def similarity_search_cosmos_db(embed_query, vector_field='vector_field', top_k=5):
    client = get_cosmos_client()
    database = client.get_database_client(azure_account_name)
    container = database.get_container_client(azure_container_name)

    # Query to do a similarity search between the embed_query and the cosmos database entries.
    # Get the text, the source (the file path) and take the 10 most relevant entries
    return list(container.query_items(
        query='SELECT TOP 10 c.text, c.source,\
            VectorDistance(c.vector_field,@embedding) AS SimilarityScore FROM c\
            ORDER BY VectorDistance(c.vector_field,@embedding)',
        parameters=[{"name": "@embedding", "value": embed_query.values}],
        enable_cross_partition_query=True))


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
    client = get_vertex_ai_client()
    print(f"Using chat model: {ai_model_final_prompt}")
    response = client.models.generate_content(
        model=ai_model_final_prompt,
        contents=prompt,
    )
    print(response)
    return "\n".join([a.text for a in response.parts])  # join the list of text values to have a single string


# The entrypoint of the core logic, to be called by test.py
def generate_ai_answer(user_prompt):
    embed_question = get_embedding(user_prompt)
    print("Question as embeddings:")
    print(embed_question.values[:100])
    sim_results = similarity_search_cosmos_db(embed_question)

    print("Context extracted from similarity search")
    for item in sim_results:
        print("- [{0}] {1}".format(item['SimilarityScore'], item['text']))
    context = "\n".join([i['text'] for i in sim_results])

    prompt = prepare_prompt(user_prompt, context)
    print("Last prompt with question and prompt")
    print(prompt)
    result = generate_answer(prompt)
    print("Final answer from the AI")
    print(result)
    return result


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
            {"role": "system", "content": answer})
        for message in st.session_state.chat_history[-1:]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])


if __name__ == "__main__":
    main()
