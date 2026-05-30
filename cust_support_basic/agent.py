import asyncio
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from langsmith.integrations.google_adk import configure_google_adk
from datetime import datetime, timedelta
import random
import uuid 

from dotenv import load_dotenv
load_dotenv()

import warnings #surpress warning
warnings.filterwarnings("ignore")

# --- 1. DEFINING TOOLS ---

def get_order_status(order_id: str) -> dict:
        """
        Get the current status of a customer order.
        args :
            order_id (str): The unique identifier for the customer's order.
         returns:
            dict: A dictionary containing the order status information.
        """

        # Dynamically generate a delivery date 3 days from today
        delivery_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")


        # In production this would call your database/API
        return {
            "order_id": order_id,
            "status": "shipped",
            "estimated_delivery": delivery_date,
            "carrier": "FedEx"
        }

def get_refund_policy() -> dict:
        """
        Get the company refund policy.
        
        returns:
        dict: A dictionary containing the refund information.
        
        """
        return {
            "window": "30 days",
            "condition": "unused and in original packaging",
            "process": "3-5 business days after approval"
        }


# --- 2. MAIN EXECUTION FLOW ---

async def main():

    # Enable LangSmith tracing for ADK
    configure_google_adk(
        name = "Customer Support Agent", #trace name
        project_name="langsmith_adk",
        metadata={
                "environment": "prod", 
                "dev": "Rahul Raj Pandey",
                "version": "1.0",
                "tools": ["get_order_status", "get_refund_policy"], 
                "Agent type": "single agent with tool"
        },
        tags=["adk", "customer-support", "v1", "single-agent-tool"],
    )

    root_agent = Agent(
        model='gemini-2.5-flash',
        name='root_agent',
        description='A helpful assistant for user questions.',
        instruction="""You are a helpful customer support agent.
        Use the available tools to answer questions about orders and refunds.
        Always be concise and accurate.""",
        tools=[get_order_status, get_refund_policy],
    )

    #Setup ADK Session and Runner
    session_service = InMemorySessionService()

    unique_session_id = f"session_{uuid.uuid4().hex[:8]}"

    session = await session_service.create_session(
           app_name="customer_support_app",
           session_id=unique_session_id,
           user_id="user_123",
    )

    runner = Runner(
        agent=root_agent,
        app_name="customer_support_app",
        session_service=session_service,
    )

    print(f"--- Starting Session: {unique_session_id} ---")

    # --- Stimulating User Input ---

    order_id = str(random.randint(10000, 99999))
    user_input_msg = f"What's the status of order #{order_id}? and also, what is your refund policy if it doesn't fit?"
    
    turn1_user_message = types.Content(
        role="user",
        parts=[types.Part(text=user_input_msg)]
    )
    print("User: ",user_input_msg)

    # Run the agent
    async for event in runner.run_async(
        user_id="user_123",
        session_id=unique_session_id,
        new_message=turn1_user_message,
    ):
        if event.is_final_response():
            print(f"Agent: {event.content.parts[0].text}")


if __name__ == "__main__":
    asyncio.run(main())


