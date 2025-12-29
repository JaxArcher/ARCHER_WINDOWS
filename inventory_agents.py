#!/usr/bin/env python3

import os
import sys
from pathlib import Path

# Set encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

def analyze_agent_file(file_path):
    """Analyze an agent file and extract key information."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return {
            'file': file_path.name,
            'error': str(e)
        }
    
    info = {
        'file': file_path.name,
        'classes': [],
        'methods': [],
        'imports': [],
        'has_handle': False,
        'has_memory': False,
        'has_init': False,
        'description': ''
    }
    
    # Extract description (first docstring or comment block)
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('"""') or line.startswith("'''"):
            # Extract docstring
            docstring = []
            start_quote = line[:3]
            j = i + 1
            while j < len(lines):
                if lines[j].startswith(start_quote):
                    break
                docstring.append(lines[j])
                j += 1
            info['description'] = '\n'.join(docstring).strip()
            break
        elif line.startswith('#') and 'ARCHER' in line:
            info['description'] = line.strip('#').strip()
            break
    
    # Extract imports
    for line in lines:
        if line.startswith('import ') or line.startswith('from '):
            info['imports'].append(line.strip())
    
    # Extract classes and methods
    in_class = False
    current_class = None
    
    for line in lines:
        if line.startswith('class '):
            class_name = line.split('class ')[1].split('(')[0].split(':')[0].strip()
            info['classes'].append(class_name)
            in_class = True
            current_class = class_name
        elif in_class and line.startswith('def '):
            method_name = line.split('def ')[1].split('(')[0].strip()
            info['methods'].append(f"{current_class}.{method_name}")
            
            if method_name == 'handle':
                info['has_handle'] = True
            elif method_name == '__init__':
                info['has_init'] = True
        elif line.startswith('class ') or (in_class and line.strip() == '' and not line.startswith(' ')):
            in_class = False
            current_class = None
    
    # Check for memory-related imports or usage
    if any('memory' in imp.lower() for imp in info['imports']):
        info['has_memory'] = True
    elif any('VectorMemory' in line or 'EpisodicMemory' in line for line in lines):
        info['has_memory'] = True
    
    return info

def main():
    agents_dir = Path("src/agents")
    
    # List of agents mentioned in spreadsheet
    expected_agents = [
        'assistant.py',
        'therapist.py', 
        'trainer.py',
        'stock_expert.py',
        'authority_manager.py',
        'evidence_processor.py',
        'federated_learning.py',
        'governance.py',
        'proactive.py'  # This might not exist
    ]
    
    print("=== AGENT INVENTORY ANALYSIS ===")
    print()
    
    # Analyze all Python files in agents directory
    all_agents = []
    for file_path in agents_dir.glob("*.py"):
        if file_path.name.startswith("_"):
            continue
            
        agent_info = analyze_agent_file(file_path)
        all_agents.append(agent_info)
    
    # Print summary
    print(f"Found {len(all_agents)} agent files")
    print()
    
    # Check expected agents
    print("Expected Agents Status:")
    print("=" * 50)
    for expected in expected_agents:
        found = any(agent['file'] == expected for agent in all_agents)
        status = "✓ FOUND" if found else "✗ MISSING"
        print(f"{status}: {expected}")
    print()
    
    # Detailed analysis of each agent
    print("Detailed Agent Analysis:")
    print("=" * 80)
    
    for agent in all_agents:
        print(f"\n📄 {agent['file']}")
        print("-" * 40)
        
        if 'error' in agent:
            print(f"❌ Error: {agent['error']}")
            continue
            
        print(f"📝 Description: {agent['description'][:100]}..." if len(agent['description']) > 100 else f"📝 Description: {agent['description']}")
        print(f"🔧 Classes: {', '.join(agent['classes'])}")
        print(f"🔄 Methods: {len(agent['methods'])} methods")
        print(f"🧠 Has handle(): {'✓' if agent['has_handle'] else '✗'}")
        print(f"💾 Has memory: {'✓' if agent['has_memory'] else '✗'}")
        print(f"🔌 Has __init__: {'✓' if agent['has_init'] else '✗'}")
        
        # Check if this is one of the expected agents
        is_expected = agent['file'] in expected_agents
        print(f"🎯 Expected: {'✓' if is_expected else '✗'}")
    
    # Create inventory markdown
    with open("logs/agent_spec_inventory.md", "w", encoding="utf-8") as f:
        f.write("# Agent Inventory Analysis\n\n")
        f.write("## Summary\n\n")
        f.write(f"Total agents found: {len(all_agents)}\n\n")
        
        f.write("## Expected Agents Status\n\n")
        f.write("| Agent | Status |\n")
        f.write("|-------|--------|\n")
        for expected in expected_agents:
            found = any(agent['file'] == expected for agent in all_agents)
            status = "✓ FOUND" if found else "✗ MISSING"
            f.write(f"| `{expected}` | {status} |\n")
        
        f.write("\n## Detailed Agent Analysis\n\n")
        
        for agent in all_agents:
            f.write(f"### {agent['file']}\n\n")
            
            if 'error' in agent:
                f.write(f"**Error**: {agent['error']}\n\n")
                continue
                
            f.write(f"**Description**: {agent['description']}\n\n")
            f.write(f"**Classes**: `{', '.join(agent['classes'])}`\n\n")
            f.write(f"**Methods**: {len(agent['methods'])} methods\n\n")
            f.write(f"**Has handle()**: {'✓' if agent['has_handle'] else '✗'}\n\n")
            f.write(f"**Has memory integration**: {'✓' if agent['has_memory'] else '✗'}\n\n")
            f.write(f"**Has __init__**: {'✓' if agent['has_init'] else '✗'}\n\n")
            f.write(f"**Expected agent**: {'✓' if agent['file'] in expected_agents else '✗'}\n\n")
            
            if agent['methods']:
                f.write("**Key Methods**:\n\n")
                for method in agent['methods'][:5]:  # Show first 5 methods
                    f.write(f"- `{method}`\n")
                if len(agent['methods']) > 5:
                    f.write(f"- ... and {len(agent['methods']) - 5} more\n")
                f.write("\n")
    
    print(f"\n📝 Inventory saved to logs/agent_spec_inventory.md")

if __name__ == "__main__":
    main()
