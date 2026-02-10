from anthropic import Anthropic
import base64
import os
from typing import Dict, Optional
from dotenv import load_dotenv
from config.states import get_state_config

# Load .env file from api directory
print("\n" + "="*60)
print("[CLAUDE.PY] Loading environment variables...")
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
print(f"[CLAUDE.PY] .env file path: {os.path.abspath(env_path)}")
print(f"[CLAUDE.PY] .env file exists: {os.path.exists(env_path)}")
# Use override=True to force .env file to override existing environment variables
load_dotenv(env_path, override=True)

# Debug: Check API key at module load time
api_key_check = os.getenv("ANTHROPIC_API_KEY")
if api_key_check:
    print(f"[CLAUDE.PY] OK - API key found!")
    print(f"[CLAUDE.PY]   Length: {len(api_key_check)} characters")
    print(f"[CLAUDE.PY]   First 20 chars: {api_key_check[:20]}...")
    print(f"[CLAUDE.PY]   Last 5 chars: ...{api_key_check[-5:]}")
else:
    print("[CLAUDE.PY] ERROR - API key NOT found!")
    print("[CLAUDE.PY] Environment variables available:")
    for key in os.environ.keys():
        if 'ANTHROPIC' in key or 'API' in key or 'KEY' in key:
            print(f"[CLAUDE.PY]   - {key}")
print("="*60 + "\n")

client = None

def get_claude_client() -> Anthropic:
    """
    Get or create Anthropic client instance
    """
    global client

    if client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")

        print("\n[CLAUDE.PY] get_claude_client() called")
        if not api_key:
            print("[CLAUDE.PY] ERROR: ANTHROPIC_API_KEY is not set!")
            raise ValueError("ANTHROPIC_API_KEY must be set in environment variables")

        print(f"[CLAUDE.PY] Creating Anthropic client...")
        print(f"[CLAUDE.PY]   Key length: {len(api_key)}")
        print(f"[CLAUDE.PY]   Key preview: {api_key[:20]}...{api_key[-5:]}")

        try:
            client = Anthropic(api_key=api_key)
            print("[CLAUDE.PY] OK - Anthropic client created successfully")
        except Exception as e:
            print(f"[CLAUDE.PY] FAILED - Error creating client: {e}")
            raise

    return client

async def analyze_contract(
    pdf_content: bytes,
    analysis_type: str = "general",
    custom_prompt: Optional[str] = None,
    state: str = "CA"
) -> Dict:
    """
    Analyze a contract PDF using Claude AI with native PDF document support.

    Sends the PDF directly to Claude as a base64-encoded document,
    eliminating the need for text extraction (which fails on scanned,
    secured, or encoding-problematic PDFs).

    Args:
        pdf_content: Raw bytes of the PDF file
        analysis_type: Type of analysis (general, risk, compliance, etc.)
        custom_prompt: Optional custom prompt for specific analysis

    Returns:
        Dictionary containing analysis results
    """
    client = get_claude_client()

    # JSON output instructions shared by all prompt types
    json_format_instructions = """

You MUST respond with valid JSON only. No markdown, no code fences, no extra text.
Use this exact structure:
{
  "overall_risk_assessment": {
    "risk_level": "HIGH" or "MEDIUM" or "LOW",
    "summary": "1-3 sentence overall risk summary for an executive audience"
  },
  "summary": {
    "critical": <number of critical issues>,
    "warning": <number of warning issues>,
    "informational": <number of informational issues>,
    "total_issues": <total number of issues>
  },
  "findings": [
    {
      "issue": "Short issue title",
      "details": "Detailed explanation of the issue",
      "category": "Category name (e.g. Legal, Financial, Operational, Compliance, Insurance, Scope, Payment, Liability)",
      "location": "Where in the contract this issue appears (section/clause reference)",
      "severity": "critical" or "warning" or "informational",
      "recommendation": "Specific actionable recommendation"
    }
  ]
}

Severity guide:
- "critical": Issues that pose significant legal, financial, or operational risk and require immediate attention
- "warning": Issues that should be addressed but are not immediately dangerous
- "informational": Notable clauses or observations that stakeholders should be aware of

"""

    # Inject state-specific context and legal checklist
    state_config = get_state_config(state)
    if state_config:
        json_format_instructions += "\n\n" + state_config["context_note"]
        json_format_instructions += "\n\nState-specific legal requirements to check:"
        for item in state_config["legal_checklist"]:
            json_format_instructions += f"\n- {item}"
    else:
        json_format_instructions += (
            "\n\nThis is a wall & ceiling / drywall subcontractor contract review "
            "for California Drywall Co. Focus on risks relevant to a specialty subcontractor."
        )

    # Define analysis prompts based on type
    prompts = {
        "general": """Analyze this wall & ceiling subcontractor contract. Identify all key terms, conditions, dates, deadlines, financial obligations, parties involved, and important clauses. Flag any issues or risks.""" + json_format_instructions,

        "risk": """Analyze this wall & ceiling subcontractor contract for potential risks including legal risks, financial risks, operational risks, compliance risks, and provide recommendations for risk mitigation.""" + json_format_instructions,

        "compliance": """Review this wall & ceiling subcontractor contract for compliance issues including regulatory compliance, industry standards, legal requirements, missing clauses or provisions, and provide recommendations for compliance improvements.""" + json_format_instructions,

        "financial": """Analyze the financial aspects of this wall & ceiling subcontractor contract including payment terms, pricing structure, financial obligations, penalties, late fees, retainage, and cost implications.""" + json_format_instructions
    }

    # Use custom prompt if provided, otherwise use predefined prompt
    if custom_prompt:
        analysis_prompt = custom_prompt + json_format_instructions
    else:
        analysis_prompt = prompts.get(analysis_type, prompts["general"])

    try:
        model_to_use = "claude-sonnet-4-20250514"
        print(f"[CLAUDE.PY] Attempting to call Claude API with model: {model_to_use}")
        print(f"[CLAUDE.PY] Sending PDF as document ({len(pdf_content)} bytes)")

        base64_pdf = base64.standard_b64encode(pdf_content).decode("utf-8")

        message = client.messages.create(
            model=model_to_use,
            max_tokens=4096,
            temperature=0.2,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": base64_pdf,
                            },
                        },
                        {
                            "type": "text",
                            "text": analysis_prompt,
                        },
                    ],
                }
            ],
        )

        print(f"[CLAUDE.PY] OK - API call successful! Model: {message.model}")

        # Extract the response
        analysis_result = message.content[0].text

        return {
            "analysis": analysis_result,
            "model": message.model,
            "tokens_used": {
                "input": message.usage.input_tokens,
                "output": message.usage.output_tokens
            }
        }

    except Exception as e:
        print(f"[CLAUDE.PY] FAILED - API call failed: {str(e)}")
        print(f"[CLAUDE.PY] Error type: {type(e).__name__}")
        raise Exception(f"Claude API error: {str(e)}")

async def summarize_contract(pdf_content: bytes) -> str:
    """
    Generate a brief summary of the contract by sending the PDF directly to Claude.
    """
    client = get_claude_client()

    try:
        model_to_use = "claude-sonnet-4-20250514"
        print(f"[CLAUDE.PY] Attempting to summarize with model: {model_to_use}")

        base64_pdf = base64.standard_b64encode(pdf_content).decode("utf-8")

        message = client.messages.create(
            model=model_to_use,
            max_tokens=1024,
            temperature=0.2,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": base64_pdf,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Provide a brief summary (2-3 paragraphs) of this contract.",
                        },
                    ],
                }
            ],
        )

        print(f"[CLAUDE.PY] OK - Summary generated successfully")
        return message.content[0].text

    except Exception as e:
        print(f"[CLAUDE.PY] FAILED - Summary failed: {str(e)}")
        raise Exception(f"Claude API error: {str(e)}")
