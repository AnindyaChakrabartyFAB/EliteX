"""
utils.py - Utility Functions for EliteX Framework

This module contains helper functions for file I/O, formatting, and output generation.
"""

import json
from pathlib import Path
from typing import Any, Dict, TextIO
from datetime import datetime


def write_section_header(f: TextIO, title: str, step_num: str = "") -> str:
    """
    Write a prominently formatted section header to file.
    
    Args:
        f: File object to write to
        title: Section title text
        step_num: Optional step number (e.g., "STEP 1")
    
    Returns:
        The formatted header string
    """
    star_line = "*" * 120
    
    header = f"\n\n{'#' * 120}\n"
    header += f"{star_line}\n"
    header += f"{star_line}\n"
    
    if step_num:
        title_text = f"{step_num}: {title.upper()}"
    else:
        title_text = title.upper()
    
    # Center the title
    padding = (120 - len(title_text)) // 2
    header += f"{'*' * padding}{title_text}{'*' * (120 - len(title_text) - padding)}\n"
    
    header += f"{star_line}\n"
    header += f"{star_line}\n"
    header += f"{'#' * 120}\n\n"
    
    f.write(header)
    return header


def write_file_header(f: TextIO, client_id: str, framework_version: str = "V6"):
    """
    Write the file header with client info and timestamp.
    
    Args:
        f: File object to write to
        client_id: Client identifier
        framework_version: Version of the framework
    """
    f.write("#" * 120 + "\n")
    f.write("*" * 120 + "\n")
    f.write("*" * 120 + "\n")
    
    if framework_version == "V6":
        title = "ELITE FINANCIAL STRATEGY FRAMEWORK V6 - STRUCTURED PYDANTIC OUTPUTS"
    else:
        title = f"ELITE FINANCIAL STRATEGY FRAMEWORK {framework_version}"
    
    padding = (120 - len(title)) // 2
    f.write(f"{'*' * padding}{title}{'*' * (120 - len(title) - padding)}\n")
    f.write("*" * 120 + "\n")
    f.write("*" * 120 + "\n")
    f.write("#" * 120 + "\n\n")
    
    f.write(f"CLIENT ID: {client_id}\n")
    f.write(f"GENERATED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"FRAMEWORK: EliteX {framework_version} (Structured Pydantic Outputs)\n\n")
    f.write("=" * 120 + "\n\n")


def write_agent_output(
    f: TextIO,
    agent_name: str,
    agent_output: Any,
    step_num: str,
    title: str,
    role: str,
    tools: str
):
    """
    Write a formatted agent output section to file.
    
    Args:
        f: File object to write to
        agent_name: Name of the agent (e.g., "manager", "investment")
        agent_output: Pydantic model output from the agent
        step_num: Step number (e.g., "STEP 1")
        title: Section title
        role: Description of agent's role
        tools: Description of tools used by agent
    """
    # Write section header
    write_section_header(f, title, step_num)
    
    # Write metadata
    f.write(f"Agent Role: {role}\n")
    f.write(f"Tools Used: {tools}\n")
    f.write("-" * 120 + "\n\n")
    f.flush()
    
    # Convert Pydantic model to JSON and write
    agent_json = agent_output.model_dump_json(indent=2)
    f.write(agent_json)
    f.write("\n\n" + "=" * 120 + "\n")
    f.write("=" * 120 + "\n\n")
    f.flush()
    
    return agent_json


def write_file_footer(f: TextIO):
    """
    Write the prominent end marker for the file.
    
    Args:
        f: File object to write to
    """
    f.write("\n" + "#" * 120 + "\n")
    f.write("*" * 120 + "\n")
    f.write("*" * 120 + "\n")
    end_title = "END OF ANALYSIS REPORT"
    padding = (120 - len(end_title)) // 2
    f.write(f"{'*' * padding}{end_title}{'*' * (120 - len(end_title) - padding)}\n")
    f.write("*" * 120 + "\n")
    f.write("*" * 120 + "\n")
    f.write("#" * 120 + "\n")
    f.flush()


def export_structured_json(
    agent_outputs: Dict[str, Any],
    json_path: Path,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Export all agent outputs to a structured JSON file.
    
    Args:
        agent_outputs: Dictionary of agent name -> Pydantic model output
        json_path: Path to JSON output file
        verbose: Whether to print progress messages
    
    Returns:
        Dictionary of structured outputs
    """
    if verbose:
        print(f"\n📊 Exporting structured Pydantic outputs to JSON...")
    
    structured_outputs = {}
    for agent_name, output in agent_outputs.items():
        # Convert Pydantic models to dict
        structured_outputs[agent_name] = output.model_dump(mode='json')
    
    with open(json_path, 'w', encoding='utf-8') as json_file:
        json.dump(structured_outputs, json_file, indent=2, ensure_ascii=False, default=str)
    
    if verbose:
        print(f"✅ JSON export complete: {json_path}")
    
    return structured_outputs


def print_completion_summary(text_log_path: Path, json_path: Path):
    """
    Print a summary of the completed analysis.
    
    Args:
        text_log_path: Path to the text log file
        json_path: Path to the JSON output file
    """
    print(f"\n🎉 V6 analysis completed with Structured Pydantic Outputs!")
    print(f"📄 Text Log: {text_log_path}")
    print(f"📊 JSON Output: {json_path}")
    print(f"\n📄 Log file structure:")
    print(f"   • STEP 1: Manager Agent Output")
    print(f"   • STEP 2: Risk & Compliance Agent Output")
    print(f"   • STEP 3: Investment Agent Output")
    print(f"   • STEP 4: Loan Agent Output")
    print(f"   • STEP 5: Banking/CASA Agent Output")
    print(f"   • STEP 5B: Bancassurance Agent Output")
    print(f"   • STEP 6: RM Strategy Agent Output (FINAL)")
    print(f"\n💡 All agent outputs are now structured Pydantic models with full validation!")


def build_rm_strategy_input(
    client_id: str,
    agent_outputs_json: Dict[str, str]
) -> str:
    """
    Build the input prompt for the RM Strategy Agent.
    
    Args:
        client_id: Client identifier
        agent_outputs_json: Dictionary of agent name -> JSON string output
    
    Returns:
        Formatted prompt string for RM Strategy Agent
    """
    return f"""
You are receiving outputs from all specialist agents for client {client_id}.
Use these outputs to create a comprehensive, actionable RM strategy.

{'='*80}
MANAGER AGENT OUTPUT:
{'='*80}
{agent_outputs_json['manager']}

{'='*80}
RISK & COMPLIANCE AGENT OUTPUT:
{'='*80}
{agent_outputs_json['risk']}

{'='*80}
INVESTMENT AGENT OUTPUT:
{'='*80}
{agent_outputs_json['investment']}

{'='*80}
LOAN AGENT OUTPUT:
{'='*80}
{agent_outputs_json['loan']}

{'='*80}
BANKING/CASA AGENT OUTPUT:
{'='*80}
{agent_outputs_json['banking']}

{'='*80}
BANCASSURANCE AGENT OUTPUT:
{'='*80}
{agent_outputs_json['bancassurance']}

{'='*80}

Based on ALL the above agent outputs, create a comprehensive RM Strategy with:
1. Concrete action items for the RM
2. Specific questions for the client (backed by data from agent outputs)
3. Detailed engagement strategy
4. Priority recommendations

Remember: Every recommendation must reference specific data from the agent outputs above.
"""

