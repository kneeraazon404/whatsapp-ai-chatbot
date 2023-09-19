# WhatsApp-integration-with-OpenAI-chatbot
WhatsApp integration with OpenAI chatbot


To Run copy and  paste these commands one by one

cd whatsapp_ai_chatbot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

uvicorn main:app --reload

ngrok http 8000

If both  are running now you can chat with the bot
