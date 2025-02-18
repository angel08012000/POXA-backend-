import uuid, os
from google.cloud.dialogflowcx_v3beta1.services.agents import AgentsClient
from google.cloud.dialogflowcx_v3beta1.services.sessions import SessionsClient
from google.cloud.dialogflowcx_v3beta1.types import session

# 路徑
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './poxa-443807-975b2060b33f.json'

def start_conversational_agent(question):
    PROJECT_ID = "poxa-443807"
    LOCATION_ID = "global"
    AGENT_ID = "e7123a23-5d51-40a4-b09e-ba643e36c390"
    AGENT = f"projects/{PROJECT_ID}/locations/{LOCATION_ID}/agents/{AGENT_ID}"
    LANGUAGE_CODE = "zh-tw"

    SESSION_ID = uuid.uuid4()
    session_path = f"{AGENT}/sessions/{SESSION_ID}"
    print(f"Session path: {session_path}\n")
    client_options = None
    agent_components = AgentsClient.parse_agent_path(AGENT)
    location_id = agent_components["location"]
    if location_id != "global":
        api_endpoint = f"{LOCATION_ID}-dialogflow.googleapis.com:443"
        print(f"API Endpoint: {api_endpoint}\n")
        client_options = {"api_endpoint": api_endpoint}

    session_client = SessionsClient(client_options=client_options)

    text_input = session.TextInput(text=question)
    query_input = session.QueryInput(text=text_input, language_code=LANGUAGE_CODE)
    request = session.DetectIntentRequest(
        session=session_path, query_input=query_input
    )
    response = session_client.detect_intent(request=request)

    print("=" * 20)
    print(f"Query text: {response.query_result.text}")
    response_messages = ""
    for msg in response.query_result.response_messages:
        response_messages = "\n".join(msg.text.text) 
    print(f"gemini 答案: {' '.join(response_messages)}\n")

    return response_messages