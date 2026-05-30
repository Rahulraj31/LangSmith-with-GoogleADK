import asyncio
import os
import random
import uuid
import warnings
warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv()

from google.adk.agents import Agent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from langsmith.integrations.google_adk import configure_google_adk


# --- 1. DEFINING TOOLS ---

def verify_package_tracking(order_id: str) -> dict:
    """
    Look up internal courier tracking logs for a specific order ID.

    args :
        order_id (str): The unique identifier for the customer's order.

    returns:
        dict: A dictionary containing the order status information.
    
    """
    # Simulating a stuck production delivery scenario
    return {
        "order_id": order_id,
        "current_status": "delayed_in_transit",
        "last_location": "Hub 4 (Mumbai)",
        "exception_reason": "Local courier delivery strike/backlog",
        "days_overdue": 5
    }

def check_compensation_policy(days_overdue: int) -> dict:
    """
    Retrieve company policy guidelines for delayed shipments.
    args :
        days_overdue (int): number of days order was delayed.
        
    returns:
        dict: A dictionary containing the compensation policy information.
    
    
    """
    return {
        "automatic_refund_eligible": False,  
        "eligibility_criteria" : "Only eligible if  7 days overdue or more",
        "compensation_offered": "Complimentary $15 voucher for next purchase",
    }


# --- 2. BUILD SUBAGENTS ---

# Sub-agent 1: Investigates the logistics database
shipping_agent = Agent(
    name="logistics_investigator_agent",
    model="gemini-2.5-flash",
    description="Investigates shipping status and flags delivery delay exceptions.",
    instruction="""Use the tracking tool to find out exactly where the order is stuck 
    and why it is overdue. Write a short, structured technical summary of your findings 
    (status, location, reason, days overdue) for the billing agent. 
    Do NOT address the customer directly or say goodbye.""",
    tools=[verify_package_tracking],
)

# Sub-agent 2: Evaluates compliance policy and writes the response
billing_agent = Agent(
    name="policy_and_resolution_agent",
    model="gemini-2.5-flash",
    description="Applies company compensation policies and handles customer communications.",
    instruction="""Review the technical shipping summary provided by the logistics agent. 
    Use your policy tool to find out what compensation the user is owed. 
    
    Draft a single, cohesive, empathetic live chat support message to the customer. 
    
    CRITICAL: Do NOT write this as an email. Do NOT include a 'Subject:' line, 
    salutations like 'Dear Customer', or placeholders like '[Your Company Name]' and NO signoff.""",
    tools=[check_compensation_policy],
)


# --- 3. MAIN EXECUTION FLOW ---
async def main():
    configure_google_adk(
        name="MultiAgent Dispute Pipeline Evaluation",
        # project_name="langsmith_adk",
        metadata={
            "environment": "prod",
            "dev": "Rahul Raj Pandey",
            "version": "1.2",
            "orchestrator": "SequentialAgent",
            "tools": ["verify_package_tracking", "check_compensation_policy"],
            "SubAgents" : ["shipping_agent", "billing_agent"],
            "Agent type": "Multi agent with tool",
        },
        tags=["adk", "multi-agent", "dispute-resolution", "v1"],
    )

    # Re-compiling the assembly line for order disputes
    dispute_pipeline = SequentialAgent(
        name="order_dispute_pipeline",
        sub_agents=[shipping_agent, billing_agent],
    )

    session_service = InMemorySessionService()
    unique_session_id = f"session_{uuid.uuid4().hex[:8]}"
    APP_NAME = "dispute_app"
    USER_ID = "user_abc"

    await session_service.create_session(
        app_name=APP_NAME,
        session_id=unique_session_id,
        user_id=USER_ID,
    )

    runner = Runner(
        agent=dispute_pipeline,
        app_name=APP_NAME,
        session_service=session_service,
    )

    print(f"--- Starting Session: {unique_session_id} for User : {USER_ID} ---")

    # The customer's complaint prompt
    random_order = str(random.randint(40000, 49999))
    message_text = f"Where is my package? Order #{random_order} was supposed to be here last Monday. I want a refund right now!"
    
    user_message = types.Content(
        role="user",
        parts=[types.Part(text=message_text)]
    )
    print(f"User: {message_text}\n")
    # Stream the sequential pipeline run
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=unique_session_id,
        new_message=user_message,
    ):
        if event.is_final_response() and event.author == "policy_and_resolution_agent":
            print(f"Agent:\n{event.content.parts[0].text}\n")



if __name__ == "__main__":
    asyncio.run(main())