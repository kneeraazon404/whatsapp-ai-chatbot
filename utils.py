import os
import pandas as pd
import openai
import chromadb
import cohere
from chromadb.utils import embedding_functions
import logging
from decouple import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Set API Keys using environment variables (ensure they're set outside this script)
openai.api_key = config("OPENAI_API_KEY")

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=openai.api_key, model_name="text-embedding-ada-002"
)
chroma_client = chromadb.Client()
collection = chroma_client.create_collection(name="my_collection")
co = cohere.Client(config("COHERE_API_KEY"))


def ingest_vectorstore():
    """Ingest data into the vectorstore."""
    df = pd.read_csv("content/adventistFAQ.csv")
    text_list = df.iloc[:, 0].dropna().tolist()
    ids = [str(i) for i in range(len(text_list))]
    collection.add(documents=text_list, ids=ids)
    logger.info("Ingested data into vectorstore.")


def get_reranked_documents(query, n_query=8, n_rerank=3):
    """Query the collection and rerank the results."""
    try:
        results = collection.query(query_texts=[query], n_results=n_query)
        if not results["documents"]:
            logger.warning(f"No documents found for query: {query}")
            return []

        documents_from_results = results["documents"][0]
        if not documents_from_results:
            logger.warning(f"No documents found for query: {query}")
            return []

        reranked_results = co.rerank(
            query=query,
            documents=documents_from_results,
            top_n=n_rerank,
            model="rerank-multilingual-v2.0",
        )
        formatted_documents = [
            f"資料{idx}：{result.document['text']}"
            for idx, result in enumerate(reranked_results, start=1)
        ]
        output = "參考資料：\n\n" + "\n\n".join(formatted_documents)
        return output
    except Exception as e:
        logger.error(f"Error in reranking documents: {e}")
        return []


def client_response(messages):
    """Simulate a client response. This function fetches input from the console."""

    print(f"Sending to Client: {messages[-1]['content']}")
    return input("Enter Client's Response: ")


def chat_response(cs_bot_conversation):
    """Generate a bot's response based on the client's message."""

    client_msg = cs_bot_conversation[-1]["content"]
    reference = get_reranked_documents(query=client_msg)
    print("相關參考資料", reference)

    # Compose the bot's message content
    system_message_content = f"""
    你是港安醫療中心的客服，請禮貌地在Whatsapp上協助客戶的問題。
    你在參考資料中可以找到港安醫療中心的相關資料。
    你是在whatsapp 上回答客戶，所以請盡量保持簡短，每次回覆盡量不多于20個字。
    {reference}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": system_message_content}]
        + cs_bot_conversation,
        temperature=1,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    print(f"Bot's Response: {response['choices'][0]['message']['content']}")

    return response["choices"][0]["message"]["content"]


# def converse(client_start, num_exchanges=5):
#     """Simulate a conversation between the client and the bot."""
#     responses = []

#     cs_bot_conversation = [{"role": "user", "content": client_start}]

#     for _ in range(num_exchanges):
#         cs_bot_content = chat_response(cs_bot_conversation)
#         cs_bot_conversation.append({"role": "assistant", "content": cs_bot_content})
#         responses.append(cs_bot_content)

#         client_content = client_response(cs_bot_conversation)
#         cs_bot_conversation.append({"role": "user", "content": client_content})

#     return responses


def bot_response(client_start):
    """Generate and return the bot's response based on the client's message."""
    cs_bot_conversation = [{"role": "user", "content": client_start}]
    cs_bot_content = chat_response(cs_bot_conversation)
    return cs_bot_content


# if __name__ == "__main__":
#     ingest_vectorstore()
#     responses = converse(client_start="太古地址係邊", num_exchanges=5)
#     for response in responses:
#         logger.info(response)
