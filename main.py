# Third-party imports
import logging

import openai
from decouple import config
from fastapi import Depends, FastAPI, Form, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from twilio.rest import Client


# Internal imports
from models import Conversation, SessionLocal
from utils import bot_response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app and set up OpenAI client
app = FastAPI()
openai.api_key = config("OPENAI_API_KEY")
whatsapp_number = config("TO_NUMBER")

client = Client(config("TWILIO_ACCOUNT_SID"), config("TWILIO_AUTH_TOKEN"))
twilio_number = config("TWILIO_NUMBER")
from_number = config("FROM_NUMBER")
to_number = config("TO_NUMBER")


# Dependency to manage database session
def get_db():
    """
    Yield a database session for the duration of the request. Close the session afterwards.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Sending message logic through Twilio Messaging API
def send_message(to_number, body_text):
    try:
        message = client.messages.create(
            from_=f"whatsapp:{twilio_number}",
            body=body_text,
            to=f"whatsapp:{to_number}",
        )
        logger.info(f"Message sent to {to_number}: {message.body}")
    except Exception as e:
        logger.error(f"Error sending message to {to_number}: {e}")


@app.post("/message")
async def reply(Body: str = Form(), db: Session = Depends(get_db)):
    """
    Listen for incoming messages, generate a response using OpenAI, store the conversation,
    and send the response back via WhatsApp.
    """
    ai_response = bot_response(Body)
    print(ai_response)
    print("Now sending message")
    # Store the conversation in the database
    try:
        conversation = Conversation(
            sender=whatsapp_number, message=Body, response=ai_response
        )
        db.add(conversation)
        db.commit()
        logger.info(f"Conversation #{conversation.id} stored in database")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error storing conversation in database: {e}")
        raise HTTPException(status_code=500, detail="Error storing conversation")

    # Send the response via WhatsApp
    try:
        send_message(whatsapp_number, ai_response)
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {e}")
        raise HTTPException(status_code=500, detail="Error sending message")

    return ""
