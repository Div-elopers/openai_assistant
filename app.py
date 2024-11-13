import logging
import os
import json
from firebase_admin import initialize_app
import openai
from dotenv import load_dotenv
from flask import Flask, request, jsonify

initialize_app()

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
assistant_id = os.getenv("ASSISTANT_ID")
client = openai.OpenAI(api_key=openai_api_key)

# Set up logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

def process_message_to_assistant(data):
    """Helper function to process messages sent to the assistant."""
    try:
        # Validate the request data
        if 'openai_thread_id' not in data or 'message_content' not in data:
            logging.warning("Missing openai_thread_id or message_content in the request data")
            return {"error": "Missing openai_thread_id or message_content"}

        # Extract data
        openai_thread_id = data['openai_thread_id']
        user_message = data['message_content']

        # Step 1: Check if openai_thread_id is None or empty
        if not openai_thread_id:
            # If no openai_thread_id is provided, create a new thread
            logging.info("No existing thread ID provided, creating a new thread.")
            new_thread = client.beta.threads.create(
                messages=[{"role": "user", "content": user_message}]
            )
            openai_thread_id = new_thread.id
            logging.info(f"Created new thread with OpenAI ID: {openai_thread_id}")
        else:
            # Add the new user message to the existing thread
            logging.info(f"Using existing OpenAI thread ID: {openai_thread_id}")
            client.beta.threads.messages.create(
                thread_id=openai_thread_id,
                role="user",
                content=user_message
            )
            thread_messages = client.beta.threads.messages.list(openai_thread_id)
            logging.info("Getting all messages from existing thread")
            logging.info(thread_messages)

        # Step 2: Run the assistant in the thread
        run = client.beta.threads.runs.create(
            thread_id=openai_thread_id,
            assistant_id="asst_KqWQr6PQAe8fu6wJuiycuaEv"
        )

        # Wait for the run to complete
        while run.status != "completed":
            run = client.beta.threads.runs.retrieve(thread_id=openai_thread_id, run_id=run.id)

        # Step 3: Retrieve only the latest assistant message after the run completes
        messages = sorted(
            client.beta.threads.messages.list(thread_id=openai_thread_id).data,
            key=lambda x: x.created_at
        )

        logging.info("Getting all messages after run")
        logging.info(messages)

        # Get the last message, which should be the assistant's response
        latest_assistant_message = messages[-1] if messages else None
        if latest_assistant_message:
            content_blocks = latest_assistant_message.content
            assistant_response = next(
                (block.text.value for block in content_blocks if block.type == 'text'), None
            )
        else:
            assistant_response = "No assistant response found."

        return {
            "openai_thread_id": openai_thread_id,
            "response": assistant_response
        }

    except Exception as e:
        logging.error(f"Internal Error: {str(e)}", exc_info=True)
        return {"error": f"Internal Error: {str(e)}"}

# Endpoint for production requests
@app.route('/send_message_to_assistant', methods=['POST'])
def send_message_to_assistant():
    data = request.json
    result = process_message_to_assistant(data)
    return jsonify(result)

# Endpoint for testing (similarly accessible via Postman)
@app.route('/test_send_message_to_assistant', methods=['POST'])
def test_send_message_to_assistant():
    data = request.json
    result = process_message_to_assistant(data)
    return jsonify(result)

# Health check endpoint
@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "running", "message": "Service is up and running"}), 200

# Saludo to the profes
@app.route('/saludo', methods=['GET'])
def saludo():
    return jsonify({"Saludo content": "Hola, soy un nuevo endpoint!"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
